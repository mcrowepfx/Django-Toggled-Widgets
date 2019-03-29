from copy import deepcopy
from itertools import chain
from warnings import warn
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.core.exceptions import ImproperlyConfigured
from django.forms import ChoiceField
from django.forms.models import ModelFormMetaclass
from django.forms.widgets import Media, Widget, Select
from django.utils import six
    
class SetupIncompleteError(ImproperlyConfigured):
    pass

class ToggledWidget(Widget):
    def __init__(self, *args, **kwargs):
        warn(
            'This class is deprecated and is no longer required.',
            DeprecationWarning
        )
        
class ToggledWidgetWrapper(object):
    """
    Wrapper class for widgets involved in a toggling relationship. This exists
    in order to exert control over whether the Django admin shows or hides the
    row containing this widget. It would be possible to simply define the
    appropriate method to achieve this on the toggled widget instances
    themselves, but since widgets of any type may be set up to toggle
    sympathetically, the choices are either to wrap them like this or monkey-
    patch, and I choose the former.
    """
    _UNDELEGATED_ATTRIBUTES = (
        'field_name',
        'widget',
        'widget_group',
        'cohorts',
        'metafield',
        'is_hidden',
        '_is_hidden',
        'lock'
    )
    
    def __init__(self, field_name, widget, group, cohorts, metafield):
        self.field_name = field_name
        self.widget = widget
        self.widget_group = group
        self.cohorts = cohorts
        self.metafield = metafield
        self._is_hidden = False
        try:
            self.is_hidden = not widget.visible
        except AttributeError:
            pass
            
    def __setattr__(self, name, value):
        if name in self._UNDELEGATED_ATTRIBUTES:
            object.__setattr__(self, name, value)
        else:
            setattr(self.widget, name, value)
            
    def __getattr__(self, name):
        return getattr(self.widget, name)
        
    def lock(self):
        """
        Locks this widget as the visible one within its group and prevents
        any further toggling from taking place either on the server or the
        client side.
        """
        self.is_hidden = True
        self.metafield.initial = self.field_name
        self.widget_group = ()
        
    @property
    def is_hidden(self):
        return self._is_hidden or self.widget.is_hidden
        
    @is_hidden.setter
    def is_hidden(self, is_hidden):
        self._is_hidden = is_hidden
        for cohort in self.cohorts:
            cohort.is_hidden = is_hidden
        if not is_hidden:
            for widget in self.widget_group:
                if widget is not self:
                    widget.is_hidden = True
        
class ToggledWidgetModelFormMetaclass(ModelFormMetaclass):
    """
    Metaclass that adds class-level hidden metafield attributes for each
    toggled field pair, which is necessary for the field to appear in the
    rendered form.
    """
    def __new__(cls, name, bases, attrs):
        if 'toggle_pairs' in attrs:
            warn(
                'The use of the "toggle_pairs" class attribute name is deprecated; please use "toggle_groups" instead.',
                DeprecationWarning
            )
            toggle_groups = attrs['toggle_pairs']
        else:
            toggle_groups = attrs['toggle_groups']
        attrs['toggle_groups'] = [ToggledWidgetModelFormMetaclass.split_group_member(m) for m in toggle_groups]
        attrs['_metafields'] = {}
        for group in attrs.get('toggle_groups', ()):
            master_field = ToggledWidgetFormMixin.split_group_member(group[0])[0]
            metafield_name = ToggledWidgetModelFormMetaclass.get_metafield_name(master_field)
            # It's probably possible to set the choices at this stage, but
            # it's somewhat awkward to do so due to the fact that the fields
            # in question might be inherited from a parent. Rather than walk
            # the inheritance tree in search of them, we can defer this to the
            # form initializer.
            attrs[metafield_name] = ChoiceField(
                widget=Select(attrs={'data-base-name': metafield_name})
            )
            attrs['_metafields'][master_field] = metafield_name
        return super(ToggledWidgetModelFormMetaclass, cls).__new__(cls, name, bases, attrs)
        
    @staticmethod
    def get_metafield_name(field_name):
        return '{}_metafield'.format(field_name)
        
    @staticmethod
    def split_group_member(member):
        """
        Helper method for dealing with the fact that any member of a toggled
        widget group may be either a single field name or a list-like object
        containing multiple field names, the first of which controls the
        toggling behavior and the remainder of which toggle sympathetically.
        """
        if isinstance(member, six.text_type):
            return (member, ())
        try:
            return (member[0], member[1:])
        except (KeyError, TypeError):
            raise TypeError(
                'Members of widget group must either be strings or sequences '
                'objects containing multiple strings.'
            )
        
class ToggledWidgetFormMixin(six.with_metaclass(ToggledWidgetModelFormMetaclass)):
    """
    Provides special handling for the initialization and submission of forms
    containing toggled widgets.
    """    
    def __init__(self, *args, **kwargs):
        super(ToggledWidgetFormMixin, self).__init__(*args, **kwargs)
        self._group_index = {}
        self._cohort_fields_index = {}
        for group in self.toggle_groups:
            metafield_name = self._metafield_index[group[0][0]]
            metafield = self.fields[metafield_name]
            self._group_index[metafield_name] = widget_group = []
            # As the initial value of the metafield, use the name of whichever
            # field has a value, defaulting to the first field in the group if
            # none do.
            initial_field = None
            for field_name, cohorts in group:
                field = self.fields[field_name]
                if getattr(self.instance, field_name, None):
                    initial_field = field
                # Each widget gets an ID that's unique within the context of
                # its fieldset.
                widget = self.get_widget(field)
                toggle_id = id(field)
                widget.attrs['data-toggle-id'] = toggle_id
                widget.attrs['data-metafield-name'] = metafield_name
                try:
                    widget.attrs['class'] += ' toggledWidget'
                except KeyError:
                    widget.attrs['class'] = 'toggledWidget'
                # Cohorts need this too
                cohort_widgets = []
                for cohort in cohorts:
                    cohort_widget = self.get_widget(self.fields[cohort])
                    cohort_widget.attrs['data-master-toggle-id'] = toggle_id
                    cohort_widgets.append(cohort_widget)
                field.widget = ToggledWidgetWrapper(
                    field_name, field.widget, widget_group, cohort_widgets, metafield
                )
                widget_group.append(field.widget)
            if not initial_field:
                initial_field = self.fields[group[0][0]]
            self.fields[metafield_name].initial = initial_field.name
            initial_field.widget.is_visible = True
        
    @staticmethod
    def build_metafield_name(field_name):
        warn(
            'ToggledWidgetFormMixin.build_metafield_name is deprecated; consider using ToggledWidgetAdminMixin instead.',
            DeprecationWarning
        )
        return ToggledWidgetModelFormMetaclass.get_metafield_name(field_name)
        
    @classmethod
    def get_widget(cls, field):
        # Widgets for choice fields in the admin are wrapped in a container;
        # you can't set attributes on these and expect them to be rendered.
        return field.widget.widget if isinstance(field.widget, RelatedFieldWidgetWrapper) else field.widget
        
    def _register_cohorts(self, field_name, cohort_names, widget):
        cohorts = []
        for cohort in cohort_names:
            self._cohort_fields_index[cohort] = field_name
            self.fields[cohort].widget = ToggledWidgetWrapper(
                self.fields[cohort].widget
            )
            cohorts.append(self.fields[cohort].widget)
        widget.set_cohorts(cohorts)
        
    def add_error(self, field, error):
        super(ToggledWidgetFormMixin, self).add_error(field, error)
        # If this error is on a field involved in a toggle relationship, make
        # sure it's visible when the form is rendered.
        if field is None:
            try:
                fields = error.error_dict.keys()
            except AttributeError:
                return
        else:
            fields = [field]
        for field in fields:
            try:
                field_instance = self.fields[self._cohort_fields_index[field]]
            except KeyError:
                if not isinstance(self.fields[field].widget, ToggledWidgetWrapper):
                    return
                field_instance = self.fields[field]
            if field_instance.widget.is_hidden:
                field_instance.widget.toggle_visibility()
        
    def clean(self, *args, **kwargs):
        cleaned_data = super(ToggledWidgetFormMixin, self).clean(*args, **kwargs)
        for master, paired in self.resolved_toggle_pairs:
            # Don't do this if the pairing has been broken
            if self.fields[master[0]].widget.paired_widget:
                metafield_value = cleaned_data[self.build_metafield_name(master[0])]
                if metafield_value == master[0]:
                    emptiable_fields = (paired[0],) + paired[1]
                else:
                    emptiable_fields = (master[0],) + master[1]
                for field in emptiable_fields:
                    cleaned_data[field] = self.fields[field].to_python('')
        return cleaned_data
        
    @property
    def media(self):
        return super(ToggledWidgetFormMixin, self).media + Media(js=(
            'admin/js/jquery.init.js',
            'admin/js/DjangoAdminFieldContext.js',
            'admin/js/ToggledWidget.js',
            'admin/js/ToggledWidget.init.js'
        ))
        
class ToggledWidgetAdminMixin(object):
    """
    ModelAdmin mixin that automatically adds all metafields to the fieldsets
    if necessary.
    """
    def get_fieldsets(self, *args, **kwargs):
        fieldsets = deepcopy(super(ToggledWidgetAdminMixin, self).get_fieldsets(*args, **kwargs))
        fields = set(chain.from_iterable(fs[1]['fields'] for fs in fieldsets))
        try:
            metafields = set(self.form._metafields.values())
            missing = tuple((metafields ^ fields) & metafields)
            if missing:
                fieldsets[0][1]['fields'] = tuple(fieldsets[0][1]['fields']) + missing
        except AttributeError:
            raise SetupIncompleteError(
                'The metafields do not appear to have been set on {}. '
                'Does it inherit from ToggledWidgetFormMixin?'.format(self.form.__name__)
            )
        return fieldsets