from functools import wraps
from io import StringIO
import traceback

from simpy.core import Simulation, Context, InterruptedException
from simpy import core


icons = dict(
init="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.8 0.0 0.8 0.0"/>
<path d="M 0.0 -0.8 0.0 0.8"/>
""",
fork="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.2 0.5 -0.2 -0.5"/>
<path d="M -0.2 -0.1 0.5 0.2"/>
<path d="M 0.4 -0.06 0.5 0.2 0.24 0.3"/>
""",
join="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.2 0.5 -0.2 -0.5"/>
<path d="M 0.5 -0.1 -0.2 0.2"/>
<path d="M -0.1 -0.06 -0.2 0.2 0.06 0.3"/>
""",
timeout="""
<circle cx="0" cy="0" r="1"/>
<path d="M 0.0 -0.8 0.0 0.0"/>
<path d="M 0.0 0.0 0.5 0.5"/>
""",
terminate="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.8 0.0 0.8 0.0"/>
""")

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
        self.node_size = scale / 2

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
        scale, node_size, y = self.scale, self.node_size, self.y
        self.active[pid] = self.y
        self.step[pid] = 'M %f %f Q %f %f %f %f %f %f %f %f L %f %f ' % (
                pid * scale - node_size / 2, y - node_size,
                pid * scale, y - node_size,
                pid * scale, y - node_size * 0.75,
                pid * scale, y - node_size / 2,
                pid * scale + node_size / 2, y - node_size / 2,
                pid * scale + node_size / 2, y - node_size / 2)
        return True

    def close(self, pid):
        scale, node_size, y = self.scale, self.node_size, self.y
        self.step[pid] += '%f %f Q %f %f %f %f %f %f %f %f Z' % (
                pid * scale + node_size / 2, y + node_size,
                pid * scale, y + node_size,
                pid * scale, y + node_size * 0.75,
                pid * scale, y + node_size / 2,
                pid * scale - node_size / 2, y + node_size / 2)

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

    def render_icon(self, name, pid, popupinfo=''):
        x, y = pid * self.scale, self.y
        self.groups['event'].write(
                '<use xlink:href="#%s-icon" '
                'transform="translate(%f %f) scale(%f)" %s/>\n' % (
                    name, x, y, self.node_size * 0.4, popupinfo))

    def fork(self, parent, child, code):
        scale, node_size, y = self.scale, self.node_size, self.y
        descr = '<h2>Fork</h2>'
        descr += self.format_code(code)
        popupinfo = self.create_popupinfo(descr)
        self.render_icon('fork', parent, popupinfo)
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    child * scale, y, parent * scale, y))
        return True

    def init(self, pid, pem, args, kwargs, code):
        descr = '<h2>Init</h2>'
        descr += '<p><span class="code">%s(%s)</span></p>' % (
                pem, ', '.join(
                    args + tuple(n + '=' + kwargs[n] for n in sorted(kwargs))))
        descr += self.format_code(code)

        scale, node_size, y = self.scale, self.node_size, self.y
        path = 'M %f %f %f %f %f %f Q %f %f %f %f %f %f %f %f Z' % (
                pid * scale - node_size / 2, y - node_size / 2,
                pid * scale + node_size / 2, y - node_size / 2,
                pid * scale + node_size / 2, y + node_size,
                pid * scale, y + node_size,
                pid * scale, y + node_size * 0.75,
                pid * scale, y + node_size / 2,
                pid * scale - node_size / 2, y + node_size / 2)

        self.render_icon('init', pid, self.create_popupinfo(descr))

        self.groups['block'].write('<path d="%s" class="state"/>\n' % path)

        self.start[pid] = y
        self.active[pid] = y
        self.wait_start[pid] = y

    def terminate(self, pid, result):
        start = self.start[pid]
        end = self.y
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="live"/>\n' % (
                    pid * self.scale, start, pid * self.scale, end))

        scale, node_size, y = self.scale, self.node_size, self.y
        self.step[pid] += '%f %f %f %f Z' % (
                pid * scale + node_size / 2, y + node_size / 2,
                pid * scale - node_size / 2, y + node_size / 2)
        self.groups['block'].write('<path d="%s" class="state"/>\n' % (
                self.step[pid]))
        self.render_icon('terminate', pid)
        del self.step[pid]

    def wait(self, pid, delay, code):
        descr = '<h2>Wait</h2>'
        descr += self.format_code(code)
        self.render_icon('timeout', pid, self.create_popupinfo(descr))

        self.wait_start[pid] = self.y
        self.close(pid)

    def join(self, parent, child, code):
        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    child.id * self.scale, self.y, parent * self.scale, self.y))

        descr = '<h2>Join</h2>'
        descr += self.format_code(code)
        self.render_icon('join', parent, self.create_popupinfo(descr))
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
        self.render_icon(evt_class, pid, self.create_popupinfo(descr))

    def __call__(self):
        scale, node_size = self.scale, self.node_size
        prev_timestep = 0
        for timestep, actions in self.history:
            self.y += scale
            prev_timestep = timestep
            timestep_start = self.y
            last_pid = None

            for idx, action in enumerate(actions):
                pid, action_type = action[0], action[1]
                if not hasattr(self, action_type): continue

                func = getattr(self, action_type)
                if not func(pid, *action[2:]) and idx + 1 < len(actions) :
                    self.y += self.node_size * 2

            timestep_end = self.y

            descr = '<p>Timestep %.2f</p>' % timestep
            popupinfo = self.create_popupinfo(descr)

            self.groups['timestep'].write(
                    '<rect x="%f" y="%f" width="%f" height="%f" '
                    'class="timestep" %s/>\n' % (
                        -scale - node_size / 2, timestep_start - node_size / 2,
                        node_size, timestep_end - timestep_start - node_size,
                        popupinfo))
        self.y += node_size

        icon_defs = ''
        for name in sorted(icons):
            icon_defs += '<g id="%s-icon" class="%s icon">%s</g>' % (
                    name, name, icons[name])

        return ('<html>\n' +
                '<head>\n'
                '<link rel="stylesheet" type="text/css" href="contrib/style.css"></link>\n' +
                '<script type="text/javascript" src="contrib/interactive.js"></script>\n' +
                '</head>\n' +
                '<body onload="init_popup()">\n' +
                '<svg height="%d" xmlns="http://www.w3.org/2000/svg">\n' % self.y +
                '<defs>\n' + icon_defs + '</defs>\n' +
                '<g transform="translate(%f, %f)">\n' % (self.scale * 2, self.scale) +
                '<filter id="dropshadow" width="150%" height="150%">\n' +
                '<feGaussianBlur in="SourceAlpha" stdDeviation="2"/>\n' +
                '<feOffset dx="2" dy="2" result="offsetblur"/>\n' +
                '<feComponentTransfer>\n' +
                '<feFuncA type="linear" slope="0.6"/>\n' +
                '</feComponentTransfer>\n' +
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
