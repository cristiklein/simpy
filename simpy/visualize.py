# TODO Fix vertical indentation on wait.
# TODO Show return values in schedule popups.
# TODO Show delay in wait popups.
# TODO Show termination line if possible
# TODO Show arguments in init popup.
# TODO Show process names on top? Maybe hover them?
# TODO Show timesteps and process steps on the left.
# TODO Don't show a step bar for external calls (like the initial fork)
# TODO Write all data into the html files. Don't reference stuff.
# TODO Draw thick line between process steps if it is alive.
# TODO Highlight lines where a process is resumed and suspended.
# TODO Figure out a better representation of the suspend cause.
# TODO How to visualize a suspend at all?
# TODO Use templates to build the visualization.
# TODO Templates should be able to build partial html fragments so that
# multiple visualization can be embedded on a single page.


from functools import wraps
from itertools import count
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
        try:
            result = func(*args, **kwargs)
        except BaseException as e:
            trace.append((False, e))
            raise
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
        self.groups['popupinfo'] = StringIO()
        self.groups['timestep'] = StringIO()
        self.groups['controlflow'] = StringIO()
        self.groups['block'] = StringIO()
        self.groups['event'] = StringIO()

        self.popup_ids = count()
        self.y = 0
        self.max_pid = 0
        self.fixup = 0
        self.terminated = False

    def create_popupinfo(self, text, code=None):
        popup_id = next(self.popup_ids)
        data = 'popups[%s] = {text: "%s"' % (popup_id,
                text.replace('"', '&quot;'))
        if code is not None:
            data += ', filename: "%s", lineno: "%s"' % code
            self.files.add(code[0])
        data += '};\n'
        self.groups['popupinfo'].write(data)
        return ('onmouseover="show_popup(arguments, %s)" '
                'onmouseout="hide_popup(arguments[0])"' % popup_id)

    def render_icon(self, name, y, pid, description, code=None):
        x = pid * self.scale
        popupinfo = self.create_popupinfo(description, code)
        self.groups['event'].write(
                '<use xlink:href="#%s-icon" '
                'transform="translate(%f %f) scale(%f)" %s></use>\n' % (
                    name, x, y, self.node_size * 0.4, popupinfo))

    def fork(self, caller, timestep, active_ctx, pem, *args, **kwargs):
        scale, node_size, y = self.scale, self.node_size, self.y
        descr = '<h2>Fork</h2>'
        pid = active_ctx.id if active_ctx is not None else -1
        self.render_icon('fork', y, pid, descr,
                caller if active_ctx is not None else None)
        self.y += self.scale
        child = yield
        self.max_pid = max(self.max_pid, child.id)

        self.groups['controlflow'].write(
                '<path d="M %f %f %f %f" class="flow"/>\n' % (
                    pid * scale, y, child.id * scale, y))

        code = (os.path.relpath(pem.__code__.co_filename),
                pem.__code__.co_firstlineno)

        descr = '<h2>Init</h2>'
        descr += '<p><span class="code">%s(%s)</span></p>' % (
                pem.__name__, '')#', '.join(
                    #tuple(str(arg) for arg in args) +
                    #tuple(n + '=' + str(kwargs[n]) for n in sorted(kwargs))))

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
        if self.y - y <= 0:
            # FIXME This is ugly but currently happens if there is a simple
            # suspend (yield None) which doesn't cause a context function call.
            self.y += self.scale
            self.fixup = self.scale
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
        self.fixup = 2 * self.scale
        self.y += self.scale

    def join(self, caller, timestep, active_ctx, ctx):
        descr = '<h2>Terminate</h2>'
        self.render_icon('terminate', self.y, active_ctx.id, descr)
        self.terminated = True
        self.y += self.scale
        self.fixup = self.scale
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

        # Increase y coordinate if this schedule happens on the termination of
        # a process.
        if self.terminated:
            self.y += self.scale
            self.fixup += self.scale

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

                timestep_start = self.y
        self.y += node_size

        # Render sourcecode.
        try:
            from pygments import highlight
            from pygments.lexers import PythonLexer
            from pygments.formatters import HtmlFormatter

            sources = {}
            lexer = PythonLexer()
            for filename in sorted(self.files):
                with open(filename) as f:
                    data = f.read()
                    hl_lines = list(range(len(data.split('\n'))))
                    formatter = HtmlFormatter(linenos=True, lineanchors='l',
                            hl_lines=hl_lines)
                    code = highlight(data, lexer, formatter)

                sources[filename] = code

            source_style = HtmlFormatter().get_style_defs('.highlight')

        except ImportError:
            # TODO Render raw.
            pass

        try:
            from jinja2 import Environment, PackageLoader
            env = Environment(loader=PackageLoader('simpy', 'templates'))
            template = env.get_template('singlepage.tmpl')
            variables = dict(
                    width=self.scale * (self.max_pid + 2),
                    height=self.y,
                    x_shift=self.scale * 1.5,
                    y_shift=self.scale,
                    icon_defs=sorted(icons.items()),
                    sources=sorted(sources.items()),
                    source_style=source_style,
            )
            for name in self.groups:
                variables[name] = self.groups[name].getvalue()

            return str(template.render(**variables))
        except ImportError:
            pass


if __name__ == '__main__':
    import sys
    import imp

    mod = imp.load_source('simulation', sys.argv[1])
    root = getattr(mod, sys.argv[2])

    sim = Simulation()
    history = trace(sim)
    # FIXME This is ugly but currently necessary, because only context methods are
    # patched right now.
    sim.context.fork(root)
    sim.simulate(until=20)

    data = SvgRenderer(history)()
    print(data)
