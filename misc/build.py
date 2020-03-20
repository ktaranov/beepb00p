#!/usr/bin/env python3
from pathlib import Path
from subprocess import check_call, run, check_output, PIPE
from tempfile import TemporaryDirectory

# TODO use injector??
# https://github.com/alecthomas/injector

# TODO def should detect stuff automatically?
# TODO make sure it's cached for feed and index page..
# TODO use threads? most of it is going to be io bound anyway



output = Path('site2')
# TODO not sure if should create it first?

# TODO make emacs a bit quieter; do not display all the 'Loading' stuff
# TODO needs to depend on compile_script and path
def compile_org(*, compile_script: Path, path: Path):
    # TODO add COMPILE_ORG to dependency?
    with TemporaryDirectory() as tdir:
        tpath = Path(tdir)
        res = run(
            [
                compile_script,
                '--output-dir', tdir,
                # '--org',  # TODO
            ],
            input=path.read_bytes(),
            stdout=PIPE,
            check=True,
        )
    out = res.stdout
    # TODO how to clean stale stuff that's not needed in output dir?
    # TODO output determined externally?
    # TODO some inputs
    outpath = output / (path.stem + '.org')
    outpath.write_bytes(res.stdout)


content = Path('content')


from typing import Dict
Meta = Dict[str, str]



# pip install ruamel.yaml -- temporary...
# just use json later?
def metadata(path: Path) -> Meta:
    meta = path.with_suffix(path.suffix + '.metadata')
    if not meta.exists():
        return {}
    from ruamel.yaml import YAML # type: ignore
    yaml = YAML(typ='safe')
    return yaml.load(meta)


# TODO allow-errors?
def compile_ipynb(*, compile_script: Path, path: Path):
    meta = metadata(path)

    # TODO make this an attribute of the notebook somehow? e.g. tag
    allow_errors = meta.get('allow_errors', False)

    # meh
    itemid = path.absolute().relative_to(content.absolute().parent)
    with TemporaryDirectory() as tdir:
        tpath = Path(tdir)
        res = run(
            [
                compile_script,
                '--output-dir', tdir,
                '--item', str(itemid),
                *(['--allow-errors'] if allow_errors else []),
            ],
            input=path.read_bytes(),
            stdout=PIPE,
            check=True,
        )
    # TODO remove duplicats
    out = res.stdout
    outpath = output / (path.stem + '.html')
    outpath.write_bytes(res.stdout)


# TODO move out?
import re
# eh, I'm not sure why hakyll chose a different template format...
# considering I adapted it with string replacement..
def hakyll_to_jinja(body: str) -> str:
    replacements = [
        ('$if('     , '{% if '         ),
        ('$endif$'  , '{% endif %}'    ),
        ('$for('    , '{% for item in '),
        ('$endfor$' , '{% endfor %}'   ),
        ('$partial(', '{% include '    ),
        (')$'       , ' %}'            ),
    ]
    for f, t in replacements:
        body = body.replace(f, t)
    body = re.sub(r'\$(\w+)\$', r'{{ \1 }}', body)

    for line in body.splitlines():
        assert '$' not in line, line
    return body


def compile_post(path: Path):
    suffix = path.suffix

    if suffix == '.org':
        compile_org(
            compile_script=Path('misc/compile_org.py'),
            path=path,
        )
    elif suffix == '.ipynb':
        # TODO make a mode to export to python?
        compile_ipynb(
            compile_script=Path('misc/compile-ipynb'),
            path=path,
        )
    else:
        raise RuntimeError(path)

from jinja2 import Environment, BaseLoader, Template # type: ignore
# TODO ugh. can't be multithreaded?
env = Environment(loader=BaseLoader())


def compile_template(*, path: Path):
    print(f'compiling {path}')
    body = hakyll_to_jinja(path.read_text())


    # globals = self.make_globals(globals)
    # TODO copy pasted from env.from_string
    cls = env.template_class
    compiled = env.compile(body, name=str(path))
    t = Template.from_code(env, compiled, globals(), None)
    # t = env.from_string(body)
    # TODO strict mode? fail if some params are missing?
    print(t.render())



def compile_templates():
    inputs = Path('templates')
    outputs = output / 'templates'
    outputs.mkdir(exist_ok=True)

    for t in inputs.glob('*.html'):
        out = outputs / t.name
        body = hakyll_to_jinja(t.read_text())
        out.write_text(body)


    from jinja2 import FileSystemLoader # type: ignore
    loader = FileSystemLoader(str(outputs))
    print(loader)


INPUTS = list(sorted({
    *content.glob('*.org'),
    *content.glob('*.ipynb'),
}))


def compile_all(max_workers=None):
    # compile_templates()
   
    from concurrent.futures import ThreadPoolExecutor
    print(INPUTS) # TODO log?
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for res in pool.map(compile_post, INPUTS):
            # need to force the iterator
            pass


def main():
    compile_all()


if __name__ == '__main__':
    main()


# TODO self check with mypy/pylint??


# TODO make sure to port todo stripping