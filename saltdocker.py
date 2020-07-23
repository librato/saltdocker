# -*- coding: utf-8 -*-
import asyncio
import datetime
import distutils.version
import json
import os
import signal
import tempfile

import aiohttp
import click
import jinja2

MINVER = distutils.version.LooseVersion('2019.2.5')
PATH = os.path.dirname(os.path.abspath(__file__))
with open(f'{PATH}/Dockerfile.j2') as dockerfile:
    DOCKERTEMPLATE = jinja2.Template(dockerfile.read())


class SaltVersion(object):

    loop = asyncio.get_event_loop()
    versions = []
    _date = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")

    def __init__(self, version):
        self.version = version

    @property
    def shortversion(self):
        return '.'.join(map(str, self.version.version[:2]))

    @classmethod
    def date(self, setting=False):
        if os.path.isfile('.lastbuild') and setting == False:
            with open('.lastbuild') as lastbuild:
                SaltVersion._date = json.load(lastbuild)['lastbuild']
        return SaltVersion._date

    async def build(self, force=False, latest=False):
        try:
            tmpfile = tempfile.mkstemp()
            with open(tmpfile[1], 'w') as dfile:
                print(DOCKERTEMPLATE.render(salt_version=str(self.version)), file=dfile)

            cwd = os.getcwd()
            if cwd != PATH:
                os.chdir(PATH)

            args = ['docker', 'build', '--file', tmpfile[1]]

            if force is True:
                args.append('--no-cache')

            if latest is True:
                args.extend([
                    '--tag', 'saltstack/salt:latest',
                ])

            args.extend([
                '--tag', f'saltstack/salt:{self.shortversion}',
                '--tag', f'saltstack/salt:{self.version}',
                '--tag', f'saltstack/salt:{self.version}-{self.date()}',
                PATH
            ])

            proc = await asyncio.create_subprocess_exec(*args, loop=self.loop)
            await proc.communicate()

        finally:
            os.chdir(cwd)
            os.unlink(tmpfile[1])

    async def push(self, latest=False, ecr="saltstack", dryrun=True):
        for tag in [
                f'salt:{self.shortversion}',
                f'salt:{self.version}',
                f'salt:{self.version}-{self.date()}',
                'salt:latest'
        ]:
            reg = f"{ecr}:{tag[5:]}"  # Remove the 'salt:' prefix
            print(tag)
            print(reg)
            if dryrun is True:
                continue
            if tag == 'latest' and latest is not True:
                continue
            if ecr != 'saltstack':
                tagproc = await asyncio.create_subprocess_exec('docker', 'tag', f'saltstack/{tag}', reg)
                await tagproc.communicate()
            proc = await asyncio.create_subprocess_exec('docker', 'push', reg)
            await proc.communicate()


    @classmethod
    def _check_version(cls, version):
        if version < MINVER or 'rc' in version.version:
            return False
        if [
                v for v in cls.data['releases']
                if distutils.version.LooseVersion(v).version[:-1] == version.version[:-1] and
                    distutils.version.LooseVersion(v) > version
        ]:
            return False
        return True

    @classmethod
    async def build_salt_images(cls, push=False, ecr=False, dryrun=True):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://pypi.org/pypi/salt/json') as response:
                cls.data = await response.json()
        versions = [distutils.version.LooseVersion('2018.3.3')]
        versions.extend(sorted(filter(cls._check_version, map(distutils.version.LooseVersion, cls.data['releases']))))
        if push is False:
            for idx, version in enumerate(versions):
                print(f'{idx}: {version}')
                if idx == 0:
                    await cls(version).build(force=True)
                else:
                    latest = version == versions[-1]
                    cls.versions.append(cls.loop.create_task(cls(version).build(latest=latest)))
        else:
            print("Push is True")
            for idx, version in enumerate(versions):
                    latest = version == versions[-1]
                    cls.versions.append(cls.loop.create_task(cls(version).push(latest=latest, ecr=ecr, dryrun=dryrun)))
        await asyncio.gather(*cls.versions, loop=cls.loop)


@click.command()
@click.option("--ecr", is_flag=True , help="Push to this ECR repo")
@click.option("--push", is_flag=True, help="Push to hub.docker.io")
@click.option("--dryrun", is_flag=True, help="Push to hub.docker.io")
def main(push, ecr, dryrun):
    loop = asyncio.get_event_loop()
    if ecr:
        # infer repo from current environment vars
        ecr_=os.environ.get('ECR')
    else:
        ecr_ = 'saltstack'
    for signame in {'SIGINT', 'SIGTERM'}:
        loop.add_signal_handler(getattr(signal, signame), loop.stop)
    try:
        if push is False:
            with open('.lastbuild', 'w') as lastbuild:
                json.dump({'lastbuild': SaltVersion.date(setting=True)}, lastbuild)
        loop.run_until_complete(SaltVersion.build_salt_images(push=push, ecr=ecr_, dryrun=dryrun))
    finally:
        loop.close()


if __name__ == '__main__':
    main()
