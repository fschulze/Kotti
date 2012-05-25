from unittest import TestCase

from mock import MagicMock
from pyramid.registry import Registry

from kotti.testing import DummyRequest
from kotti.testing import UnitTestBase


class TestNestedMutationDict(TestCase):
    def test_dictwrapper_basics(self):
        from kotti.util import NestedMutationDict

        data = {}
        wrapper = NestedMutationDict(data)
        changed = wrapper.changed = MagicMock()

        wrapper['name'] = 'andy'
        assert data == {'name': 'andy'}
        assert wrapper == {'name': 'andy'}
        assert wrapper['name'] == 'andy'
        assert changed.call_count == 1

        wrapper['age'] = 77
        assert data == {'name': 'andy', 'age': 77}
        assert wrapper['age'] == 77
        assert wrapper['name'] == 'andy'
        assert changed.call_count == 2

        wrapper['age'] += 1
        assert data == {'name': 'andy', 'age': 78}
        assert wrapper['age'] == 78
        assert changed.call_count == 3

    def test_listwrapper_basics(self):
        from kotti.util import NestedMutationList

        data = []
        wrapper = NestedMutationList(data)
        changed = wrapper.changed = MagicMock()

        wrapper.append(5)
        assert data == [5]
        assert wrapper == [5]
        assert wrapper[0] == 5
        assert changed.call_count == 1

        wrapper.insert(0, 33)
        assert data == [33, 5]
        assert wrapper[0] == 33
        assert changed.call_count == 2

        del wrapper[0]
        assert data == [5]
        assert wrapper[0] == 5
        assert changed.call_count == 3

    def test_dictwrapper_wraps(self):
        from kotti.util import NestedMutationDict
        from kotti.util import NestedMutationList

        wrapper = NestedMutationDict(
            {'name': 'andy', 'age': 77, 'children': []})
        changed = wrapper.changed = MagicMock()

        wrapper['name'] = 'randy'
        assert changed.call_count == 1

        assert isinstance(wrapper['children'], NestedMutationList)
        wrapper['children'].append({'name': 'sandy', 'age': 33})
        assert changed.call_count == 2
        assert len(wrapper['children']), 1
        assert isinstance(wrapper['children'][0], NestedMutationDict)

    def test_listwrapper_wraps(self):
        from kotti.util import NestedMutationDict
        from kotti.util import NestedMutationList

        wrapper = NestedMutationList(
            [{'name': 'andy', 'age': 77, 'children': []}])
        changed = wrapper.changed = MagicMock()

        assert isinstance(wrapper[0], NestedMutationDict)
        assert isinstance(wrapper[0]['children'], NestedMutationList)
        assert changed.call_count == 0


class TestRequestCache(UnitTestBase):
    def setUp(self):
        from kotti.util import request_cache

        registry = Registry('testing')
        request = DummyRequest()
        request.registry = registry
        super(TestRequestCache, self).setUp(registry=registry, request=request)
        self.cache_decorator = request_cache

    def test_it(self):
        from kotti.util import clear_cache

        called = []

        @self.cache_decorator(lambda a, b: (a, b))
        def my_fun(a, b):
            called.append((a, b))

        my_fun(1, 2)
        my_fun(1, 2)
        self.assertEqual(len(called), 1)
        my_fun(2, 1)
        self.assertEqual(len(called), 2)

        clear_cache()
        my_fun(1, 2)
        self.assertEqual(len(called), 3)

    def test_dont_cache(self):
        from kotti.util import DontCache
        called = []

        def dont_cache(a, b):
            raise DontCache

        @self.cache_decorator(dont_cache)
        def my_fun(a, b):
            called.append((a, b))

        my_fun(1, 2)
        my_fun(1, 2)
        self.assertEqual(len(called), 2)


class TestLRUCache(TestRequestCache):
    def setUp(self):
        from kotti.util import lru_cache

        super(TestLRUCache, self).setUp()
        self.cache_decorator = lru_cache


class TestTitleToName(TestCase):
    def test_max_length(self):
        from kotti.util import title_to_name
        assert len(title_to_name(u'a' * 50)) == 40

    def test_normal(self):
        from kotti.util import title_to_name
        assert title_to_name(u'Foo Bar') == u'foo-bar'

    def test_disambiguate_name(self):
        from kotti.util import disambiguate_name
        assert disambiguate_name(u'foo') == u'foo-1'
        assert disambiguate_name(u'foo-3') == u'foo-4'


class TestSnippets(TestCase):
    def setUp(self):
        from kotti.views.util import snippet_regexp
        self.regexp = snippet_regexp
        self.results = []

    def tearDown(self):
        del self.results

    def _sub(self, match):
        infos = match.groupdict()
        if infos['selfclosing'] is None and infos['content'] is None:
            return match.group(0)
        self.results.append(match)
        return 'matched%s' % len(self.results)

    def test_snippet_name_chars(self):
        out = self.regexp.sub(self._sub, "slkdfj [Moo_foo-2000 egg=ham]Blubber[/Moo_foo-2000] slkdfj")
        assert out == "slkdfj matched1 slkdfj"
        assert len(self.results) == 1
        assert self.results[0].groupdict()['name'] == 'Moo_foo-2000'

    def test_selfclosing(self):
        out = self.regexp.sub(self._sub, "slkdfj [foo egg=ham/] slkdfj")
        assert out == "slkdfj matched1 slkdfj"
        assert len(self.results) == 1
        assert self.results[0].groupdict() == {
            'arguments': ' egg=ham',
            'content': None,
            'escapeclose': '',
            'escapeopen': '',
            'name': 'foo',
            'selfclosing': '/'}
        assert self.results[0].groups() == (
            '', 'foo', ' egg=ham', '/', None, '')

    def test_normal(self):
        out = self.regexp.sub(self._sub, "slkdfj [bar egg=ham]Blubber[/bar] slkdfj")
        assert out == "slkdfj matched1 slkdfj"
        assert len(self.results) == 1
        assert self.results[0].groupdict() == {
            'arguments': ' egg=ham',
            'content': 'Blubber',
            'escapeclose': '',
            'escapeopen': '',
            'name': 'bar',
            'selfclosing': None}
        assert self.results[0].groups() == (
            '', 'bar', ' egg=ham', None, 'Blubber', '')

    def test_escaped(self):
        out = self.regexp.sub(self._sub, "slkdfj [[foo egg=ham/]] slkdfj")
        assert len(self.results) == 1
        assert self.results[0].groupdict() == {
            'arguments': ' egg=ham',
            'content': None,
            'escapeclose': ']',
            'escapeopen': '[',
            'name': 'foo',
            'selfclosing': '/'}
        assert self.results[0].groups() == (
            '[', 'foo', ' egg=ham', '/', None, ']')

    def test_not_selfclosing(self):
        out = self.regexp.sub(self._sub, "slkdfj [foo egg=ham] slkdfj")
        assert len(self.results) == 0

    def test_two_not_selfclosing(self):
        out = self.regexp.sub(self._sub, "slkdfj [foo egg=ham] [bar egg=ham] slkdfj")
        assert len(self.results) == 0

    def test_non_matching_names(self):
        out = self.regexp.sub(self._sub, "slkdfj [foo egg=ham]Blubber[/bar] slkdfj")
        assert len(self.results) == 0

    def test_quotes_in_args(self):
        out = self.regexp.sub(self._sub, "slkdfj [foo egg='ham/]'/] slkdfj")
        assert out == "slkdfj matched1'/] slkdfj"
