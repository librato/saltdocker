# -*- coding: utf-8 -*-


def test_check_all_versions_built(date, versions, docker):
    tags = set()
    for image in docker.images.list():
        tags.update(image.tags)
    expected_tags = {'saltstack/salt:latest'}
    for version in versions:
        shortversion = '.'.join(version.split('.')[:2])
        expected_tags.update([version, f'{version}-{date}'])
    print(expected_tags)
    print(tags)
    assert expected_tags.issubset(tags)
