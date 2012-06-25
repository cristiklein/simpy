from functools import wraps
from io import StringIO
import os
import traceback

from simpy.core import Simulation, Context, Interrupt
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
timeout="""
<circle cx="0" cy="0" r="1"/>
<path d="M 0.0 -0.8 0.0 0.0"/>
<path d="M 0.0 0.0 0.5 0.5"/>
""",
resume_success="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.3 0.3 0.0 0.5 0.5 -0.5"/>
""",
resume_failure="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.6 -0.6 0.6 0.6"/>
<path d="M 0.0 -0.6 -0.6 0.6"/>
""",
terminate="""
<circle cx="0" cy="0" r="1"/>
<path d="M -0.8 0.0 0.8 0.0"/>
""")


def trace_func(simulation, trace, func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        stack = traceback.extract_stack(limit=2)
        filename = os.path.relpath(stack[0][0])
        lineno = stack[0][1]

        caller = (filename, lineno)
        trace.append((True, caller, simulation.now, simulation.active_proc,
            func.__name__, args, kwargs))
        result = func(*args, **kwargs)
        trace.append((False, result))
        return result
    return wrapper


def trace(simulation):
    history = []

    # Overwrite context function with tracer functions.
    for name, func in simulation.context_funcs.items():
        tracer = trace_func(simulation, history, func)
        setattr(simulation.context, name, tracer)

    simulation.process = trace_func(simulation, history, simulation.process)
    simulation.schedule = trace_func(simulation, history, simulation.schedule)
    simulation.join = trace_func(simulation, history, simulation.join)

    return history


class SvgRenderer(object):
    def __init__(self, history, scale=40, expand=True):
        self.history = history
        self.scale = scale
        self.node_size = scale / 2

        self.expand = expand

        self.files = set()

        self.groups = {}
        self.groups['timestep'] = StringIO()
        self.groups['controlflow'] = StringIO()
        self.groups['block'] = StringIO()
        self.groups['event'] = StringIO()

        self.y = self.scale

    def create_popupinfo(self, text, code=None):
        args = '\'%s\'' % text.replace('"', '&quot;')
        if code is not None:
            filename, lineno = code
            self.files.add(filename)
            args += ', \'%s\', %d' % (filename, lineno)
        return ('onmouseover="show_popup(arguments, %s)" '
                'onmouseout="hide_popup(arguments[0])"' % args)

    def render_icon(self, name, y, pid, description, code=None):
        x = pid * self.scale
        popupinfo = self.create_popupinfo(description, code)
        self.groups['event'].write(
                '<use xlink:href="#%s-icon" '
                'transform="translate(%f %f) scale(%f)" %s/>\n' % (
                    name, x, y, self.node_size * 0.4, popupinfo))

    def fork(self, caller, timestep, active_ctx, pem, *args, **kwargs):
        scale, node_size, y = self.scale, self.node_size, self.y
        descr = '<h2>Fork</h2>'
        pid = active_ctx.id if active_ctx is not None else -1
        self.render_icon('fork', y, pid, descr, caller)
        self.y += self.scale
        child = yield

        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    pid * scale, y, child.id * scale, y))

        code = (os.path.relpath(pem.__code__.co_filename),
                pem.__code__.co_firstlineno)

        descr = '<h2>Init</h2>'
        descr += '<p><span class="code">%s(%s)</span></p>' % (
                pem, ', '.join(
                    tuple(str(arg) for arg in args) +
                    tuple(n + '=' + str(kwargs[n]) for n in sorted(kwargs))))

        path = 'M %f %f %f %f %f %f %f %f %f %f Z' % (
                child.id * scale - node_size / 2, y - node_size / 2,
                child.id * scale + node_size / 2, y - node_size / 2,
                child.id * scale + node_size / 2, y + node_size / 2,
                child.id * scale, y + node_size,
                child.id * scale - node_size / 2, y + node_size / 2)

        self.render_icon('init', y, child.id, descr, code)

        self.groups['block'].write('<path d="%s" class="state"/>\n' % path)
        self.y += scale
        self.fixup = self.scale

    def process(self, caller, timestep, active_ctx, ctx):
        scale, node_size, y = self.scale, self.node_size, self.y
        pid = ctx.id
        self.fixup = 0
        self.terminated = False
        path = 'M %f %f %f %f %f %f ' % (
                pid * scale - node_size / 2, y - node_size,
                pid * scale, y - node_size / 2,
                pid * scale + node_size / 2, y - node_size)
        yield
        y = self.y - self.fixup
        if not self.terminated:
            path += '%f %f %f %f %f %f Z' % (
                    pid * scale + node_size / 2, y + node_size / 2,
                    pid * scale, y + node_size,
                    pid * scale - node_size / 2, y + node_size / 2)
        else:
            path += '%f %f %f %f Z' % (
                    pid * scale + node_size / 2, y + node_size / 2,
                    pid * scale - node_size / 2, y + node_size / 2)

        self.groups['block'].write('<path d="%s" class="state"/>\n' % path)

    def resume(self, caller, timestep, active_ctx, other, value=None):
        descr = '<h2>Resume</h2>'
        self.render_icon('timeout', self.y, active_ctx.id, descr, caller)
        self.y += self.scale
        yield
        self.fixup = self.scale

    def wait(self, caller, timestep, active_ctx, delay=None):
        descr = '<h2>Wait</h2>'
        self.render_icon('timeout', self.y, active_ctx.id, descr, caller)
        self.y += self.scale
        yield
        self.fixup = self.scale

    def join(self, caller, timestep, active_ctx, ctx):
        descr = '<h2>Terminate</h2>'
        self.render_icon('terminate', self.y, active_ctx.id, descr, caller)
        self.terminated = True
        yield

    def schedule(self, caller, timestep, active_ctx, ctx, evt_type,
            value, at=None):
        # Draw a controlflow line from the caller to callee.
        src_pid = active_ctx.id if active_ctx is not None else -1
        tgt_pid = ctx.id

        if tgt_pid == src_pid:
            # This only happens for the initial fork schedule and waits.
            # Draw a vertical line and increase y position.
            self.groups['controlflow'].write(
                    '<path d="M %f %f %f %f" class="flow"/>\n' % (
                        src_pid * self.scale, self.y - self.scale,
                        src_pid * self.scale, self.y))
        else:
            self.groups['controlflow'].write(
                    '<path d="M %f %f %f %f" class="flow"/>\n' % (
                        src_pid * self.scale, self.y,
                        tgt_pid * self.scale, self.y))

        if evt_type:
            descr = '<h2>Success</h2>'
            self.render_icon('resume_success', self.y, tgt_pid, descr)
        else:
            descr = '<h2>Failure</h2>'
            self.render_icon('resume_failure', self.y, tgt_pid, descr)
        yield

    def __call__(self):
        scale, node_size = self.scale, self.node_size
        timestep_start = 0
        renderer_stack = []
        for trace in self.history:
            if trace[0]:
                # A function was about to be called.
                caller, timestep, active_ctx, fname, args, kwargs = trace[1:]

                if not hasattr(self, fname):
                    renderer_stack.append(None)
                    continue
                func = getattr(self, fname)

                renderer = func(caller, timestep, active_ctx,
                        *args, **kwargs)
                next(renderer)

                # Push call onto the stack.
                renderer_stack.append(renderer)
            else:
                # A function call has succeeded.
                result = trace[1:]

                renderer = renderer_stack.pop()
                if renderer is not None:
                    try:
                        renderer.send(result[0])
                    except StopIteration:
                        pass

            if not renderer_stack:
                timestep_end = self.y

                descr = '<p>Timestep %.2f</p>' % timestep
                popupinfo = self.create_popupinfo(descr)

                self.groups['timestep'].write(
                        '<rect x="%f" y="%f" width="%f" height="%f" '
                        'class="timestep" %s/>\n' % (
                            -scale - node_size / 2, timestep_start - node_size / 2,
                            node_size, timestep_end - timestep_start - node_size,
                            popupinfo))

                self.y += scale
                timestep_start = self.y
        self.y += node_size

        icon_defs = ''
        for name in sorted(icons):
            icon_defs += '<g id="%s-icon" class="%s icon">%s</g>' % (
                    name, name, icons[name])

        # Render sourcecode.
        sourcecode_style = StringIO()
        sourcecode = StringIO()

        try:
            from pygments import highlight
            from pygments.lexers import PythonLexer
            from pygments.formatters import HtmlFormatter

            sourcecode_files = []
            lexer = PythonLexer()
            for filename in sorted(self.files):
                with open(filename) as f:
                    data = f.read()
                    hl_lines = list(range(len(data.split('\n'))))
                    formatter = HtmlFormatter(linenos=True, lineanchors='l',
                            hl_lines=hl_lines)
                    code = highlight(data, lexer, formatter)

                sourcecode_files.append((
                        filename,
                        '<div id="%s">%s</div>\n' % (filename, code)))

            sourcecode_style.write(
                    HtmlFormatter().get_style_defs('.highlight'))

            sourcecode.write('<div class="navbar"><ul>%s</ul></div>\n' % (
                    ''.join(['<li onclick="show_source(\'%s\')">%s</li>' % (
                            filename, filename)
                        for filename, code in sourcecode_files])))

            sourcecode.write('<div name="page">\n')
            for idx, (filename, code) in enumerate(sourcecode_files):
                cls = 'hidden' if idx != 0 else ''
                sourcecode.write('<div name="%s" class="%s">' % (
                    filename, cls))
                sourcecode.write(code)
                sourcecode.write('</div>\n')
            sourcecode.write('</div>\n')

        except ImportError:
            # TODO Render raw.
            pass

        return ('<html>\n' +
                '<head>\n'
                '<link rel="stylesheet" type="text/css" href="contrib/style.css"></link>\n' +
                '<script type="text/javascript" src="contrib/interactive.js"></script>\n' +
                '<style>\n' + sourcecode_style.getvalue() + '</style>\n' +
                '</head>\n' +
                '<body onload="init_popup()">\n' +
                '<div class="visualization">\n' +
                '<div class="simulation-flow">\n' +
                '<svg height="%d" xmlns="http://www.w3.org/2000/svg">\n' % self.y +
                '<defs>\n' + icon_defs + '</defs>\n' +
                '<g transform="translate(%f, %f)">\n' % (self.scale * 1.5, 0) +
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
                '</svg></div>\n' +
                '<div name="sourcecode" class="sourcecode">\n' +
                sourcecode.getvalue() +
                '</div>\n' +
                '</div>\n' +
                '</body>\n' +
                '</html>\n')


def root(ctx):
    def p1(ctx):
        yield ctx.wait(2)

    ctx.fork(p1)
    yield ctx.fork(p1)
    yield ctx.wait(1)

from simpy.resource import Resource

def root(ctx, result=[]):
    resource = Resource(ctx, 'res')

    def child(ctx, name, resource, result):
        yield resource.request()
        result.append((name, ctx.now))
        yield ctx.wait(1)
        resource.release()

    ctx.fork(child, 'a', resource, result)
    ctx.fork(child, 'b', resource, result)
    yield

sim = Simulation()
history = trace(sim)
sim.fork(root)
sim.simulate(until=20)

from pprint import pprint
pprint(history)

with open('test.html', 'w') as f:
    data = SvgRenderer(history)()
    f.write(data)
