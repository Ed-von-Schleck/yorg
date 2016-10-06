'''Builds info for developers.'''
from os import system
from .build import path, ver_branch, exec_cmd, devinfo_path_str


def __clean_pylint(pylint_out):
    '''Cleans pylint stuff.'''
    clean_out = ''
    skipping = False
    err_str = 'No config file found, using default configuration'
    lines = [line for line in pylint_out.split('\n') if line != err_str]
    for line in lines:
        if line == 'Traceback (most recent call last):':
            skipping = True
        elif line == 'RuntimeError: maximum recursion depth exceeded ' + \
                     'while calling a Python object':
            skipping = False
        elif not skipping:
            clean_out += line + '\n'
    return clean_out


def __process(src, cond, outfile):
    '''Appends a file.'''
    if cond(src):
        return
    outfile.write('    '+str(src)+'\n')
    out_pylint = __clean_pylint((exec_cmd('pylint -r n '+str(src))))
    out_pyflakes = exec_cmd('pyflakes '+str(src))
    out_pep8 = exec_cmd('pep8 ' + str(src))
    outs = [out.strip() for out in [out_pylint, out_pyflakes, out_pep8]]
    map(lambda out: outfile.write(out+'\n'), [out for out in outs if out])
    outfile.write('\n')


def build_devinfo(target, source, env):
    '''This function creates the
    `pep8 <https://www.python.org/dev/peps/pep-0008>`_,
    `Pylint <http://www.pylint.org>`_ and
    `pyflakes <https://pypi.python.org/pypi/pyflakes>`_ code reports.'''
    name = env['NAME']
    dev_conf = env['DEV_CONF']
    for fname, cond in dev_conf.items():
        for src in source:
            with open(('%s%s.txt') % (path, fname), 'a') as outfile:
                __process(src, cond, outfile)
    names, rmnames = '', ''
    for fname in dev_conf:
        names += fname + '.txt '
        rmnames += '{path}' + fname + '.txt '
    build_command_str = \
        'tar -czf {out_name} -C {path} ' + names + ' && rm ' + rmnames
    fpath = devinfo_path_str.format(path=path, name=name, version=ver_branch)
    build_command = build_command_str.format(path=path, out_name=fpath)
    system(build_command)