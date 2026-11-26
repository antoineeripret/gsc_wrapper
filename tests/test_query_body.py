"""
Tests for the request body built by the Query object (no API call).
"""
import pytest
import pandas as pd
from gscwrapper.query import Query, Report


@pytest.fixture
def query():
    """
    Fixture that returns a Query object without any service, as we only check the raw request body.
    """
    return Query(service=None, webproperty='sc-domain:example.com')


# brandedClassification

def test_branded_classification_as_dimension(query):
    """Test that brandedClassification can be used to group the data."""
    query.dimensions(['date', 'brandedClassification'])
    assert query.raw['dimensions'] == ['date', 'brandedClassification']


@pytest.mark.parametrize('value', ['BRANDED', 'NON_BRANDED'])
def test_branded_classification_as_filter(query, value):
    """Test that brandedClassification can be used as a filter with the equals operator."""
    query.filter('brandedClassification', value)
    assert query.raw['dimensionFilterGroups'] == [{
        'groupType': 'and',
        'filters': [{'dimension': 'brandedClassification', 'expression': value, 'operator': 'equals'}]
    }]


@pytest.mark.parametrize('operator', ['notEquals', 'contains', 'notContains', 'includingRegex', 'excludingRegex'])
def test_branded_classification_rejects_other_operators(query, operator):
    """Test that brandedClassification only accepts the equals operator."""
    with pytest.raises(ValueError, match='equals operator'):
        query.filter('brandedClassification', 'BRANDED', operator)


@pytest.mark.parametrize('value', ['branded', 'UNKNOWN', ''])
def test_branded_classification_rejects_invalid_values(query, value):
    """Test that brandedClassification only accepts BRANDED or NON_BRANDED."""
    with pytest.raises(ValueError, match='BRANDED or NON_BRANDED'):
        query.filter('brandedClassification', value)


def test_branded_classification_filter_after_query_filter(query):
    """Test that brandedClassification cannot be filtered once query is filtered."""
    query.filter('query', 'shoes', 'contains')
    with pytest.raises(ValueError, match='query filter'):
        query.filter('brandedClassification', 'BRANDED')


def test_query_filter_after_branded_classification_filter(query):
    """Test that query cannot be filtered once brandedClassification is filtered."""
    query.filter('brandedClassification', 'BRANDED')
    with pytest.raises(ValueError, match='query filter'):
        query.filter('query', 'shoes', 'contains')


def test_branded_classification_dimension_after_query_filter(query):
    """Test that the data cannot be grouped by brandedClassification once query is filtered."""
    query.filter('query', 'shoes', 'contains')
    with pytest.raises(ValueError, match='query filter'):
        query.dimensions(['brandedClassification'])


def test_query_filter_after_branded_classification_dimension(query):
    """Test that query cannot be filtered once the data is grouped by brandedClassification."""
    query.dimensions(['brandedClassification'])
    with pytest.raises(ValueError, match='query filter'):
        query.filter('query', 'shoes', 'contains')


def test_branded_classification_with_query_dimension(query):
    """Test that grouping by query and brandedClassification is allowed (only a query filter is forbidden)."""
    query.dimensions(['query', 'brandedClassification']).filter('brandedClassification', 'NON_BRANDED')
    assert query.raw['dimensions'] == ['query', 'brandedClassification']


def test_report_detects_branded_classification_as_dimension():
    """Test that the Report object classifies brandedClassification as a dimension, not a metric."""
    df = pd.DataFrame({
        'brandedClassification': ['BRANDED', 'NON_BRANDED'],
        'clicks': [10, 20],
        'impressions': [100, 200],
    })
    report = Report(df, 'sc-domain:example.com')
    assert report.dimensions == ['brandedClassification']
    assert report.metrics == ['clicks', 'impressions']


# webMultimodal

def test_search_type_web_multimodal(query):
    """Test that webMultimodal is an accepted search type."""
    query.search_type('webMultimodal')
    assert query.raw['type'] == 'webMultimodal'


# filter_list

@pytest.mark.parametrize('dimension, expressions', [
    ('country', ['fra', 'bel']),
    ('device', ['MOBILE', 'TABLET']),
])
def test_filter_list(query, dimension, expressions):
    """Test that filter_list writes a filterLists entry in a new filter group."""
    query.filter_list(dimension, expressions)
    assert query.raw['dimensionFilterGroups'] == [{
        'groupType': 'and',
        'filterLists': [{'dimension': dimension, 'expressions': expressions}]
    }]


def test_filter_list_on_existing_group(query):
    """Test that filter_list uses the last filter group, like filter."""
    query.filter('page', 'blog', 'contains').filter_list('country', ['fra']).filter_list('device', ['MOBILE'])
    assert query.raw['dimensionFilterGroups'] == [{
        'groupType': 'and',
        'filters': [{'dimension': 'page', 'expression': 'blog', 'operator': 'contains'}],
        'filterLists': [
            {'dimension': 'country', 'expressions': ['fra']},
            {'dimension': 'device', 'expressions': ['MOBILE']},
        ]
    }]


@pytest.mark.parametrize('dimension', ['page', 'query', 'searchAppearance', 'date', 'brandedClassification'])
def test_filter_list_rejects_invalid_dimension(query, dimension):
    """Test that filter_list only accepts the country and device dimensions."""
    with pytest.raises(ValueError, match='Dimension not valid'):
        query.filter_list(dimension, ['value'])


def test_filter_list_rejects_empty_expressions(query):
    """Test that filter_list requires at least one expression."""
    with pytest.raises(ValueError, match='at least one expression'):
        query.filter_list('country', [])


def test_filter_list_rejects_non_list_expressions(query):
    """Test that filter_list requires a list of expressions."""
    with pytest.raises(TypeError, match='must be a list'):
        query.filter_list('country', 'fra')


def test_filter_list_after_filter_on_same_dimension(query):
    """Test that a dimension already used in filters cannot be used in filterLists."""
    query.filter('country', 'fra')
    with pytest.raises(ValueError, match='already filtered'):
        query.filter_list('country', ['bel'])


def test_filter_after_filter_list_on_same_dimension(query):
    """Test that a dimension already used in filterLists cannot be used in filters."""
    query.filter_list('device', ['MOBILE', 'TABLET'])
    with pytest.raises(ValueError, match='already filtered'):
        query.filter('device', 'DESKTOP')


def test_filter_after_filter_list(query):
    """Test that filter works on a filter group created by filter_list (no KeyError)."""
    query.filter_list('country', ['fra', 'bel']).filter('page', 'blog', 'contains')
    assert query.raw['dimensionFilterGroups'] == [{
        'groupType': 'and',
        'filterLists': [{'dimension': 'country', 'expressions': ['fra', 'bel']}],
        'filters': [{'dimension': 'page', 'expression': 'blog', 'operator': 'contains'}]
    }]


# groupType

@pytest.mark.parametrize('group_type', ['or', 'AND', 'And', ''])
def test_filter_rejects_invalid_group_type(query, group_type):
    """Test that filter only accepts the and group type (the only value accepted by the API)."""
    with pytest.raises(ValueError, match='Group type not valid'):
        query.filter('page', 'blog', 'contains', group_type=group_type)


@pytest.mark.parametrize('group_type', ['or', 'AND', 'And', ''])
def test_filter_list_rejects_invalid_group_type(query, group_type):
    """Test that filter_list only accepts the and group type (the only value accepted by the API)."""
    with pytest.raises(ValueError, match='Group type not valid'):
        query.filter_list('country', ['fra', 'bel'], group_type=group_type)


def test_filter_rejects_invalid_group_type_on_existing_group(query):
    """Test that an invalid group type is rejected, not silently dropped, when a filter group already exists."""
    query.filter('page', 'blog', 'contains')
    with pytest.raises(ValueError, match='Group type not valid'):
        query.filter('query', 'shoes', 'contains', group_type='or')


def test_filter_list_rejects_invalid_group_type_on_existing_group(query):
    """Test that an invalid group type is rejected, not silently dropped, when a filter group already exists."""
    query.filter('page', 'blog', 'contains')
    with pytest.raises(ValueError, match='Group type not valid'):
        query.filter_list('country', ['fra', 'bel'], group_type='or')


def test_explicit_and_group_type(query):
    """Test that an explicit and group type is accepted by filter and filter_list."""
    query.filter('page', 'blog', 'contains', group_type='and').filter_list('country', ['fra'], group_type='and')
    assert query.raw['dimensionFilterGroups'] == [{
        'groupType': 'and',
        'filters': [{'dimension': 'page', 'expression': 'blog', 'operator': 'contains'}],
        'filterLists': [{'dimension': 'country', 'expressions': ['fra']}]
    }]
