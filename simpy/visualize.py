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

    def get_code(self, depth):
        stack = traceback.extract_stack(limit=depth+1)
        filename, lineno = stack[0][:2]
        surround = 5
        with open(filename) as f:
            lines = f.readlines()
            code = []
            for i in range(lineno - (surround + 1), lineno + surround):
                if i < 0: continue
                if i >= len(lines): break
                code.append((i == lineno - 1, lines[i][:-1]))
        return code

    def create_context(self, pem, args, kwargs):
        pid = self.active_ctx.id if self.active_ctx is not None else -1

        ctx = VisualizationContext(self, self._get_id(), pem, args, kwargs)
        self.record((pid, Fork, ctx.id, pem.__name__,
            tuple(str(arg) for arg in args),
            dict((name, str(kwargs[arg])) for name in kwargs),
            self.get_code(3)))
        return ctx

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
    def __init__(self, history, scale=20, expand=True):
        self.history = history
        self.scale = scale
        self.expand = expand

        self.groups = {}
        self.groups['timestep'] = StringIO()
        self.groups['controlflow'] = StringIO()
        self.groups['block'] = StringIO()
        self.groups['event'] = StringIO()

        self.start = {}
        self.active = {}
        self.y = self.scale
        self.y_ofs = self.scale / 2

    def enter(self, pid, evt_type):
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    -self.scale, self.y, pid * self.scale, self.y))

        self.active[pid] = self.y

    def leave(self, pid, evt_type):
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

    def create_popupinfo(self, text):
        text = text.replace('"', '&quot;')
        return ('onmouseover="show_popup(arguments, \'%s\')" '
                'onmouseout="hide_popup(arguments[0])"' % text)

    def format_code(self, code):
        s = '<p>Code:</p><div class="code">'
        for active, line in code:
            cls = ''
            if active:
                cls += ' active'
            line = line.replace('\'', '\\\'')
            s += '<p class="%s">%s</p>' % (cls, line)
        s += '</div>'
        return s

    def fork(self, parent, child, pem, args, kwargs, code):
        descr = '<h2>Fork</h2>'
        descr += '<p>Call: <span class="code">%s(%s)</span></p>' % (
                pem,
                ', '.join(args +
                    tuple(n + '=' + kwargs[n] for n in sorted(kwargs))))
        descr += self.format_code(code)
        popupinfo = self.create_popupinfo(descr)
        self.groups['event'].write(
                '<circle cx="%f" cy="%f" r="%f" '
                'class="fork" %s/>\n' % (
                    parent * self.scale, self.y, self.scale / 8, popupinfo))
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    child * self.scale, self.y, parent * self.scale, self.y))

        self.groups['block'].write(
                '<rect x="%f" y="%f" width="%f" height="%f" '
                'class="init"/>\n' % (
                    child * self.scale - self.scale / 8, self.y - self.y_ofs/2,
                    self.scale / 4, self.y_ofs))

        self.start[child] = self.y + self.y_ofs/2
        self.active[child] = self.y + self.y_ofs/2

    def terminate(self, pid, result):
        start = self.start[pid]
        end = self.y
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="live"/>\n' % (
                    pid * self.scale, start, pid * self.scale, end))
        return True

    def wait(self, pid, delay, code):
        return True

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

    def schedule(self, pid, src_id, delay, evt_type, value, code):
        if pid != src_id:
            # This should only happen for timeouts.
            self.groups['controlflow'].write(
                    '<path d="M %f %f %f %f" class="flow"/>\n' % (
                        src_id * self.scale, self.y, pid * self.scale, self.y))

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

            for action in actions:
                pid, action_type = action[0], action[1]
                if not hasattr(self, action_type): continue

                func = getattr(self, action_type)
                if not func(pid, *action[2:]):
                    self.y += self.y_ofs


            timestep_end = self.y
        self.y += self.y_ofs * 2

        return ('<html>\n' +
                '<head>\n'
                '<link rel="stylesheet" type="text/css" href="contrib/style.css"></link>\n' +
                '<script type="text/javascript" src="contrib/interactive.js"></script>\n' +
                '</head>\n' +
                '<body onload="init_popup()">\n' +
                '<svg height="%d" xmlns="http://www.w3.org/2000/svg">\n' % self.y +
                '<g transform="translate(%f, %f)">\n' % (self.scale * 2, self.scale) +
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
    f.write(data)
