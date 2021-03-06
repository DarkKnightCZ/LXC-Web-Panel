import os
from datetime import datetime

from fabric.api import local, task, lcd
from pytz.reference import LocalTimezone


def generate_package_date():
    """
    Reads the system date and time, including the timezone and returns
    a formatted date string suitable for use in the Debian changelog file:

    Example output: Mon, 23 Dec 2013 11:41:00 +1200
    """
    today = datetime.now()
    localtime = LocalTimezone()
    date_with_timezone = today.replace(tzinfo=localtime)
    return date_with_timezone.strftime('%a, %d %b %Y %H:%M:%S %z')


def generate_debian_changelog(version):
    """
    We don't store the debian/changelog file in the GIT repository, but build
    it each time from the current GIT tag.
    """
    with open('debian/changelog', 'w') as f:
        f.write('lwp ({0}) unstable; urgency=low\n\n  * LWP release {0}\n\n'.format(version))
        f.write(' -- Claudio Mignanti <c.mignanti@gmail.com>  {}\n'.format(generate_package_date()))


def get_version_from_debian_changelog():
    """
    Returns the version of the latest package from the debian changelog.

    Because we build the changelog first anyway (see: create_debian_changelog),
    this should return the same version as "git describe --tags".
    """
    return local('dpkg-parsechangelog --show-field Version', capture=True)


def get_deb_architecture():
    """
    Returns the deb architecture of the local system, e.g. amd64, i386, arm
    """
    return local('dpkg --print-architecture', capture=True)


@task(alias='deb')
def debian():
    version = local('git describe --tag', capture=True)
    with open('lwp/version', 'w') as fd:
        fd.write('{}\n'.format(version))

    # the debian changelog is not stored on GIT and rebuilt each time
    generate_debian_changelog(version)
    local('sudo dpkg-buildpackage -us -uc -b')

    # dpkg-buildpackage places debs one folder above
    package = 'lwp_{}_all.deb'.format(version)

    # finally, move package into gh-pages dir
    target = 'debian-testing' if 'rc' in version else 'debian'
    local('sudo mv ../{} gh-pages/{}/'.format(package, target))
    local('sudo rm ../lwp_*.changes')
    if (os.environ['USER'] == 'claudyus'):
        local('sudo dpkg-sig -k 0DFD7CBB --sign builder gh-pages/{}/{}'.format(target, package))


@task
def clone():
    if not os.path.exists('gh-pages'):
        local('git clone git@github.com:claudyus/LXC-Web-Panel.git gh-pages')

    with lcd('gh-pages'):
        local('git checkout origin/gh-pages -b gh-pages || true')


@task(alias='assets')
def build_assets():
    """
    Runs the assets pipeline, Grunt, bower, sass, etc.
    """
    # only run npm install when needed
    if not os.path.exists('jsbuild/node_modules'):
        with lcd('jsbuild'):
            local('npm install')

    # run Bower, then Grunt
    with lcd('jsbuild'):
        local('node_modules/.bin/bower install')
        local('node_modules/.bin/grunt')


@task
def site():
    clone()
    build_assets()
    debian()
    local('make -C gh-pages/')


@task
def clean_assets():
    local('rm -rf lwp/static/js/vendor')
    local('rm -f lwp/static/css/bootstrap.*')

@task
def clean_jsbuild():
    local('rm -rf jsbuild/node_modules')
    local('rm -rf jsbuild/bower_components')

@task
def clean():
    clean_jsbuild()
    clean_assets()
