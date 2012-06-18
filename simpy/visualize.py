from functools import wraps
from io import StringIO
import traceback

from simpy.core import Simulation, Context, InterruptedException
from simpy import core


class VisualizationContext(Context):
    def wait(self, delay=None):
        self.sim.record((self.id, Wait, delay, self.sim.get_code(3)))
        return Context.wait(self, delay)

    def join(self, target):
        self.sim.record((self.id, Join, target, self.sim.get_code(2)))
        return Context.join(self, target)

    def __repr__(self):
        return Context.__str__(self)


Init = 'init'
Terminate = 'terminate'
Fork = 'fork'
Wait = 'wait'
Join = 'join'
Schedule = 'schedule'
Enter = 'enter'
Leave = 'leave'

class VisualizationSim(Simulation):
    def __init__(self, *args, **kwargs):
        self.history = []
        Simulation.__init__(self, *args, **kwargs)
        # Mark initial timestep.
        self.history[0] = (-1, self.history[0][1])

    def record(self, item):
        if not self.history or self.history[-1][0] < self.now:
            self.history.append((self.now, []))

        self.history[-1][1].append(item)

    def extract_lines(self, filename, lineno, surround=5):
        with open(filename) as f:
            lines = f.readlines()
            code = []
            for i in range(lineno - (surround + 1), lineno + surround):
                if i < 0: continue
                if i >= len(lines): break
                code.append((i == lineno - 1, lines[i][:-1]))
        return code

    def get_code(self, depth):
        stack = traceback.extract_stack(limit=depth+1)
        filename, lineno = stack[0][:2]
        return self.extract_lines(filename, lineno)

    def create_context(self, pem, args, kwargs):
        pid = self.active_ctx.id if self.active_ctx is not None else -1

        ctx_id = self._get_id()
        self.record((pid, Fork, ctx_id, self.get_code(3)))

        code = self.extract_lines(pem.__code__.co_filename,
                pem.__code__.co_firstlineno)
        self.record((ctx_id, Init, pem.__name__,
            tuple(str(arg) for arg in args),
            dict((name, str(kwargs[arg])) for name in kwargs),
            code))

        return VisualizationContext(self, ctx_id, pem, args, kwargs)

    def destroy_context(self, ctx):
        self.record((ctx.id, Terminate, ctx.result))
        return Simulation.destroy_context(self, ctx)

    def schedule(self, ctx, delay, evt_type, value):
        pid = self.active_ctx.id if self.active_ctx is not None else -1

        self.record((ctx.id, Schedule, pid, delay, evt_type, value,
            self.get_code(4)))
        return Simulation.schedule(self, ctx, delay, evt_type, value)

    def step(self):
        # We need to set self.now right here because it will be used by
        # self.record().
        self.now = self.events[0][0]
        pid = self.events[0][1]
        evt_type = self.events[0][3]

        self.record((pid, Enter, evt_type))
        result = Simulation.step(self)
        self.record((pid, Leave, evt_type))
        return result


class SvgRenderer(object):
    def __init__(self, history, scale=40, expand=True):
        self.history = history
        self.scale = scale
        self.expand = expand

        self.groups = {}
        self.groups['timestep'] = StringIO()
        self.groups['controlflow'] = StringIO()
        self.groups['block'] = StringIO()
        self.groups['event'] = StringIO()

        self.start = {}
        self.wait_start = {}
        self.active = {}
        self.step = {}
        self.y = self.scale
        self.y_ofs = self.scale / 2

    def enter(self, pid, evt_type):
        self.active[pid] = self.y
        self.step[pid] = 'M %f %f Q %f %f %f %f %f %f %f %f L %f %f ' % (
                pid * self.scale - self.scale / 8, self.y - self.scale / 8,
                pid * self.scale, self.y - self.scale / 8,
                pid * self.scale, self.y - self.scale / 16,
                pid * self.scale, self.y,
                pid * self.scale + self.scale / 8, self.y,
                pid * self.scale + self.scale / 8, self.y)

    def leave2(self, pid, evt_type):
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    pid * self.scale, self.y, -self.scale, self.y))
        # TODO Check if process is alive.
        self.groups['block'].write(
                '<rect x="%f" y="%f" width="%f" height="%f" '
                'class="state"/>\n' % (
                    pid * self.scale - self.scale / 8, self.active[pid],
                    self.scale / 4, self.y - self.active[pid]))
        self.active[pid] = self.y

    def close(self, pid):
        self.step[pid] += '%f %f Q %f %f %f %f %f %f %f %f Z' % (
                pid * self.scale + self.scale / 8, self.y + self.scale / 8,
                pid * self.scale, self.y + self.scale / 8,
                pid * self.scale, self.y + self.scale / 16,
                pid * self.scale, self.y,
                pid * self.scale - self.scale / 8, self.y)

        self.groups['block'].write('<path d="%s" class="state"/>\n' % (
                self.step[pid]))
        del self.step[pid]

    def create_popupinfo(self, text):
        text = text.replace('"', '&quot;')
        return ('onmouseover="show_popup(arguments, \'%s\')" '
                'onmouseout="hide_popup(arguments[0])"' % text)

    def format_code(self, code):
        s = '<p>Code:</p><div class="code">'
        for active, line in code:
            cls = ''
            if active:
                cls = 'class="active"'
            line = line.replace('\'', '\\\'')
            s += '<p %s>%s</p>' % (cls, line)
        s += '</div>'
        return s

    def fork(self, parent, child, code):
        descr = '<h2>Fork</h2>'
        descr += self.format_code(code)
        popupinfo = self.create_popupinfo(descr)
        self.groups['event'].write(
                '<circle cx="%f" cy="%f" r="%f" '
                'class="fork" %s/>\n' % (
                    parent * self.scale, self.y, self.scale / 8, popupinfo))
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    child * self.scale, self.y, parent * self.scale, self.y))
        return True

    def init(self, pid, pem, args, kwargs, code):
        descr = '<h2>Init</h2>'
        descr += '<p><span class="code">%s(%s)</span></p>' % (
                pem, ', '.join(
                    args + tuple(n + '=' + kwargs[n] for n in sorted(kwargs))))
        descr += self.format_code(code)

        self.groups['block'].write(
                '<rect x="%f" y="%f" width="%f" height="%f" '
                'class="init" %s/>\n' % (
                    pid * self.scale - self.scale / 8, self.y - self.y_ofs/2,
                    self.scale / 4, self.y_ofs, self.create_popupinfo(descr)))

        self.start[pid] = self.y + self.y_ofs/2
        self.active[pid] = self.y + self.y_ofs/2
        self.wait_start[pid] = self.y

    def terminate(self, pid, result):
        start = self.start[pid]
        end = self.y
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="live"/>\n' % (
                    pid * self.scale, start, pid * self.scale, end))

        self.step[pid] += '%f %f %f %f Z' % (
                pid * self.scale + self.scale / 8, self.y,
                pid * self.scale - self.scale / 8, self.y)
        self.groups['block'].write('<path d="%s" class="state"/>\n' % (
                self.step[pid]))
        del self.step[pid]
        return True

    def wait(self, pid, delay, code):
        descr = '<h2>Wait</h2>'
        descr += self.format_code(code)
        popupinfo = self.create_popupinfo(descr)
        self.groups['event'].write(
                '<circle cx="%f" cy="%f" r="%f" '
                'class="wait" %s/>\n' % (
                    pid * self.scale, self.y, self.scale / 8, popupinfo))

        self.wait_start[pid] = self.y
        self.close(pid)

    def join(self, parent, child, code):
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    child.id * self.scale, self.y, parent * self.scale, self.y))

        descr = '<h2>Join</h2>'
        descr += self.format_code(code)
        popupinfo = self.create_popupinfo(descr)
        self.groups['event'].write(
                '<circle cx="%f" cy="%f" r="%f" '
                'class="join" %s/>\n' % (
                    parent * self.scale, self.y, self.scale / 8, popupinfo))
        self.close(parent)

    def schedule(self, pid, src_id, delay, evt_type, value, code):
        if pid == src_id:
            # This should only happen for timeouts.
            start = self.wait_start.pop(pid)
            self.groups['controlflow'].write(
                    '<path d="M %f %f %f %f %f %f %f %f" class="flow"/>\n' % (
                        pid * self.scale, start,
                        pid * self.scale + self.scale * 0.5, start,
                        pid * self.scale + self.scale * 0.5, self.y,
                        pid * self.scale, self.y))

        if evt_type == core.Timeout:
            evt_class = 'timeout'
        elif evt_type == core.Join:
            evt_class = 'join'
        elif evt_type == core.Crash:
            evt_class = 'crash'
        elif evt_type == core.Interrupt:
            evt_class = 'interrupt'
        else:
            raise RuntimeError('Unknown event type %d' % evt_type)

        descr = '<h2>%s</h2>' % evt_class.title()
        descr += self.format_code(code)
        popupinfo = self.create_popupinfo(descr)
        self.groups['event'].write(
                '<circle cx="%f" cy="%f" r="%f" '
                'class="%s" %s/>\n' % (
                    pid * self.scale, self.y, self.scale / 8, evt_class,
                    popupinfo))

    def __call__(self):
        prev_timestep = 0
        for timestep, actions in self.history:
            self.y += (timestep - prev_timestep) * self.scale
            prev_timestep = timestep
            timestep_start = self.y
            last_pid = None

            for idx, action in enumerate(actions):
                pid, action_type = action[0], action[1]
                if not hasattr(self, action_type): continue

                func = getattr(self, action_type)
                if not func(pid, *action[2:]) and idx + 1 < len(actions) :
                    self.y += self.y_ofs

            timestep_end = self.y

            descr = '<p>Timestep %.2f</p>' % timestep
            popupinfo = self.create_popupinfo(descr)
            self.groups['timestep'].write(
                    '<rect x="%f" y="%f" width="%f" height="%f" '
                    'class="timestep" %s/>\n' % (
                        -self.scale - self.scale / 8, timestep_start,
                        self.scale / 4, timestep_end - timestep_start,
                        popupinfo))
        self.y += self.y_ofs * 2

        return ('<html>\n' +
                '<head>\n'
                '<link rel="stylesheet" type="text/css" href="contrib/style.css"></link>\n' +
                '<script type="text/javascript" src="contrib/interactive.js"></script>\n' +
                '</head>\n' +
                '<body onload="init_popup()">\n' +
                '<svg height="%d" xmlns="http://www.w3.org/2000/svg">\n' % self.y +
                '<g transform="translate(%f, %f)">\n' % (self.scale * 2, self.scale) +
                '<filter id="dropshadow" width="150%" height="150%">\n' +
                '<feGaussianBlur in="SourceAlpha" stdDeviation="2"/>\n' +
                '<feOffset dx="2" dy="2" result="offsetblur"/>\n' +
                '<feMerge>\n' +
                '<feMergeNode/>\n' +
                '<feMergeNode in="SourceGraphic"/>\n' +
                '</feMerge>\n' +
                '</filter>\n' +
                self.groups['timestep'].getvalue() +
                self.groups['controlflow'].getvalue() +
                self.groups['block'].getvalue() +
                self.groups['event'].getvalue() +
                '</g>\n' +
                '</svg>\n' +
                '</body>\n' +
                '</html>\n')


def root(ctx):
    def p1(ctx):
        yield ctx.wait(2)

    yield ctx.join(ctx.fork(p1))
    yield ctx.wait(1)

sim = VisualizationSim(root)
sim.simulate(until=20)

with open('test.html', 'w') as f:
    data = SvgRenderer(sim.history)()
    from pprint import pprint
    pprint(sim.history)
    f.write(data)
