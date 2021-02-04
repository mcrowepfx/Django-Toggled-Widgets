import sys
from copy import deepcopy
from itertools import chain
from warnings import warn
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.core.exceptions import ImproperlyConfigured
from django.forms import ChoiceField
from django.forms.boundfield import BoundField
from django.forms.models import ModelFormMetaclass
from django.forms.utils import pretty_name
from django.forms.widgets import Media, Widget, ChoiceWidget, Select, HiddenInput

class SetupIncompleteError(ImproperlyConfigured):
    pass

class MetafieldWidget(Select):
    """
    Widget that renders itself as a toggling button if there are only two
    total options and as a <select> element otherwise.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option_count = 0

    def create_option(self, *args, **kwargs):
        self.option_count += 1
        return super().create_option(*args, **kwargs)

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        if self.option_count == 2:
            attrs = context['widget']['attrs']
            try:
                attrs['class'] += ' toggle-button'
            except KeyError:
                attrs['class'] = 'toggle-button'
        return context

class LabellessBoundField(BoundField):
    def label_tag(self, *args, **kwargs):
        return ''

class Metafield(ChoiceField):
    def get_bound_field(self, form, field_name):
        return LabellessBoundField(form, self, field_name)

class ToggledWidget(Widget):
    toggle_button_text = None

    def __init__(self, *args, **kwargs):
        warn(
            'This class is deprecated and is no longer required.',
            DeprecationWarning
        )
        super().__init__(*args, **kwargs)

    def get_metafield_label(self):
        return self.toggle_button_text or ''

class ToggledWidgetMixin:
    metafield_label = None

    def get_metafield_label(self):
        """
        This method should return the text label that should be visible within
        the metafield when this widget is visible. Note that when
        MetafieldWidget is used to render a metafield with only two possible
        values, the visible label likely needs to refer to the other possible
        option (i.e. when field X is visible, the metafield should say
        something about switching to field Y), which is somewhat
        counterintuitive.
        """
        return self.metafield_label

class ToggledWidgetCohortWrapper:
    """
    Wrapper class for cohorts of widgets that control a toggling relationship.
    """
    _UNDELEGATED_ATTRIBUTES = (
        'widget',
        'is_hidden',
        '_is_hidden',
        '_set_visibility',
        'attrs'
    )

    def __init__(self, widget):
        self.widget = widget
        self._is_hidden = False
        # Widgets for choice fields in the admin are wrapped in a container,
        # which means that in order to set HTML attributes on them, you have
        # to drill down.
        self.attrs = widget.widget.attrs if isinstance(widget, RelatedFieldWidgetWrapper) else widget.attrs

    def __setattr__(self, name, value):
        if name in self._UNDELEGATED_ATTRIBUTES:
            object.__setattr__(self, name, value)
        else:
            setattr(self.widget, name, value)

    def __getattr__(self, name):
        return getattr(self.widget, name)

    def _set_visibility(self, is_hidden):
        self._is_hidden = is_hidden

    @property
    def is_hidden(self):
        return self._is_hidden or self.widget.is_hidden

    @is_hidden.setter
    def is_hidden(self, is_hidden):
        self._set_visibility(is_hidden)

class ToggledWidgetWrapper(ToggledWidgetCohortWrapper):
    """
    Wrapper class for widgets that control a toggling relationship.
    """
    _UNDELEGATED_ATTRIBUTES = ToggledWidgetCohortWrapper._UNDELEGATED_ATTRIBUTES + (
        'field_name',
        'widget_group',
        'cohorts',
        'metafield',
        'lock',
        # These are aliases for backward compatibility, subject to future removal
        'set_visible',
        'break_pairing'
    )

    def __init__(self, widget, field_name, group, cohorts, metafield):
        super().__init__(widget)
        self.field_name = field_name
        self.widget_group = group
        for cohort in cohorts:
            if not isinstance(cohort, ToggledWidgetCohortWrapper):
                raise TypeError(
                    'Cohort widgets must be ToggledWidgetCohortWrapper instances.'
                )
        self.cohorts = cohorts
        self.metafield = metafield

    def lock(self):
        """
        Locks this widget as the visible one within its group and prevents
        any further toggling from taking place either on the server or the
        client side.
        """
        if self.is_hidden:
            self.is_hidden = False
        self.widget_group = ()
        # Do this to prevent the metafield from showing up
        self.metafield.widget = HiddenInput()

    def _set_visibility(self, is_hidden):
        super()._set_visibility(is_hidden)
        for cohort in self.cohorts:
            cohort.is_hidden = is_hidden
        if not is_hidden:
            for widget in self.widget_group:
                if widget is not self:
                    widget.is_hidden = True
            self.metafield.initial = self.field_name

    # Aliases for backward compatibility
    def set_visible(self):
        self.is_hidden = False

    def break_pairing(self):
        self.lock()

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
            toggle_groups = attrs.get('toggle_groups')
        # Only proceed with this if the class actually defines toggle groups;
        # otherwise we might override behavior defined in a base class.
        if toggle_groups:
            attrs['toggle_groups'] = []
            for group in toggle_groups:
                attrs['toggle_groups'].append(
                    [ToggledWidgetModelFormMetaclass.split_group_member(m) for m in group]
                )
            # This index associates each field name involved in a toggle
            # relationship (including cohorts) with the name of the
            # corresponding metafield.
            attrs['_metafield_index'] = {}
            metafield_widgets = attrs.get('metafield_widgets', {})
            for group in attrs['toggle_groups']:
                field_names = tuple(member[0] for member in group)
                metafield_name = ToggledWidgetModelFormMetaclass.get_metafield_name(field_names[0])
                metafield_widget = None
                for field_name in field_names:
                    if field_name in metafield_widgets:
                        metafield_widget = metafield_widgets[field_name]
                        if isinstance(metafield_widget, Widget):
                            raise ImproperlyConfigured(
                                'Metafield widget classes, not instances, must be specified.'
                            )
                        if not issubclass(metafield_widget, ChoiceWidget):
                            raise ImproperlyConfigured(
                                'Metafield widget classes must inherit from django.forms.widgets.ChoiceWidget.'
                            )
                        break
                if not metafield_widget:
                    metafield_widget = MetafieldWidget
                # It's probably possible to set the choices at this stage, but
                # it's somewhat awkward to do so due to the fact that the fields
                # in question might be inherited from a parent. Rather than walk
                # the inheritance tree in search of them, we can defer this to the
                # form initializer.
                attrs[metafield_name] = Metafield(
                    widget=metafield_widget(attrs={'class': 'toggle-metafield'})
                )
                for field_name in chain.from_iterable(group):
                    attrs['_metafield_index'][field_name] = metafield_name
        return super().__new__(cls, name, bases, attrs)

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
        if isinstance(member, str):
            return (member, ())
        try:
            return (member[0], member[1:])
        except (KeyError, TypeError):
            raise TypeError(
                'Members of widget group must either be strings or sequences '
                'objects containing multiple strings.'
            )

class ToggledWidgetFormMixin(metaclass=ToggledWidgetModelFormMetaclass):
    """
    Provides special handling for the initialization and submission of forms
    containing toggled widgets.
    """
    # This should be an iterable of tuples describing the toggle groups. Each
    # tuple element may be a single string whose value is a field to be
    # toggled, or a tuple whose first value is such a field and whose
    # remaining values are additional fields to be toggled sympathetically
    # with the first.
    toggle_groups = None
    # This dict should associate a field name from a toggle group with the
    # widget class to be used to render the metafield. The widget class must
    # inherit from django.forms.widgets.ChoiceWidget. The name of any field in
    # a toggle group may be used as the key.
    metafield_widgets = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__modify_fields__(*args, **kwargs)
        self._group_index = {}
        self._cohort_fields_index = {}
        if self.toggle_groups is None:
            raise SetupIncompleteError('This class must define the toggle_groups attribute.')
        self._setup()

    def _setup(self):
        for group_id, group in enumerate(self.toggle_groups):
            toggle_id_iterator = iter(range(len(self.toggle_groups), sys.maxsize))
            metafield_name = self._metafield_index[group[0][0]]
            metafield = self.fields[metafield_name]
            metafield.widget.attrs['data-toggle-group-id'] = group_id
            metafield.choices = []
            self._group_index[metafield_name] = widget_group = []
            # As the initial value of the metafield, use the name of whichever
            # field has a value, defaulting to the first field in the group if
            # none do.
            initial_field = None
            for field_name, cohorts in group:
                field = self.fields[field_name]
                if getattr(self.instance, field_name, None):
                    initial_field = field_name
                # Each widget gets an ID that's unique within the context of
                # its fieldset, and each toggled widget group gets such an ID.
                # Cohorts also get tied to the controlling widget via its ID.
                toggle_id = next(toggle_id_iterator)
                cohort_widgets = []
                for cohort in cohorts:
                    self.fields[cohort].widget = ToggledWidgetCohortWrapper(
                        self.fields[cohort].widget
                    )
                    self.fields[cohort].widget.attrs['data-master-toggle-id'] = toggle_id
                    cohort_widgets.append(self.fields[cohort].widget)
                    self._cohort_fields_index[cohort] = field_name
                field.widget = ToggledWidgetWrapper(
                    field.widget, field_name, widget_group, cohort_widgets, metafield
                )
                widget_group.append(field.widget)
                try:
                    if 'toggled-widget' not in field.widget.attrs['class']:
                        field.widget.attrs['class'] += ' toggled-widget'
                except KeyError:
                    field.widget.attrs['class'] = 'toggled-widget'
                field.widget.attrs['data-toggle-id'] = toggle_id
                field.widget.attrs['data-toggle-group-id'] = group_id
                try:
                    metafield_label = field.widget.get_metafield_label()
                except AttributeError:
                    metafield_label = None
                metafield.choices.append((
                    field_name, metafield_label or field.label or pretty_name(field_name)
                ))
            # Skip this for bound forms; the field value will come from the
            # form data, so set it during cleaning.
            if not self.is_bound:
                if not initial_field:
                    initial_field = group[0][0]
                self.fields[initial_field].widget.is_hidden = False

    @staticmethod
    def build_metafield_name(field_name):
        warn(
            'ToggledWidgetFormMixin.build_metafield_name is deprecated; consider using ToggledWidgetAdminMixin instead.',
            DeprecationWarning
        )
        return ToggledWidgetModelFormMetaclass.get_metafield_name(field_name)

    def __modify_fields__(self, *args, **kwargs):
        """
        This is a hook for subclasses to modify fields during initialization.
        Subclasses should do so via this hook rather than in the constructor,
        as the latter must perform setup on the widgets to wrap them
        appropriately, and therefore the toggling won't work properly on any
        fields modified after this class constructor finishes (though
        subclasses are free to override the constructor to do other things).
        The same arguments passed to the constructor are passed here.
        """

    def add_error(self, field, error):
        super().add_error(field, error)
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
                field_instance = self.fields[field]
                if not isinstance(field_instance.widget, ToggledWidgetWrapper):
                    continue
            field_instance.widget.is_hidden = False

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        # Unset the values of any currently inactive fields
        for group in self.toggle_groups:
            metafield_value = cleaned_data[self._metafield_index[group[0][0]]]
            for field_name, cohorts in group:
                if field_name == metafield_value:
                    self.fields[field_name].widget.is_hidden = False
                else:
                    cleaned_data[field_name] = self.fields[field_name].to_python('')
                    for cohort in cohorts:
                        cleaned_data[cohort] = self.fields[cohort].to_python('')
        return cleaned_data

    @property
    def media(self):
        return super().media + Media(js=(
            'admin/js/jquery.init.js',
            'admin/js/DjangoAdminFieldContext.js',
            'admin/js/ToggledWidget.js',
            'admin/js/ToggledWidget.init.js'
        ), css={'all': ('admin/css/ToggledWidget.css',)})

class ToggledWidgetAdminMixin:
    """
    ModelAdmin mixin that automatically adds all metafields to the fieldsets
    if necessary.
    """
    def _insert_metafield(self, field_list, metafield, after):
        if metafield not in field_list:
            # The fields in the list won't necessarily be in the same order as
            # the fields involved in the toggle group, so find whichever one
            # appears latest in the list and insert it after that.
            last_index = None
            for field_name in after:
                try:
                    idx = field_list.index(field_name)
                    if idx > (last_index or 0):
                        last_index = idx
                except ValueError:
                    # This would mean that the field that should have preceded
                    # the metafield isn't there. It's possible this could be
                    # valid.
                    pass
            if last_index is None:
                raise ValueError(
                    'Could not find any of the fields {} in the given list.'.format(
                        ', '.join(after)
                    )
                )
            field_list.insert(last_index + 1, metafield)

    def get_fields(self, request, obj=None):
        fields = list(deepcopy(super().get_fields(request, obj)))
        form = self._get_form_for_get_fields(request, obj)
        try:
            for group in form.toggle_groups:
                field_names = [member[0] for member in group]
                metafield = form._metafield_index[field_names[0]]
                # If the metafield is already there, remove it so we can
                # insert it at the proper position.
                try:
                    fields.pop(fields.index(metafield))
                except ValueError:
                    pass
                self._insert_metafield(fields, metafield, field_names)
            return fields
        except AttributeError:
            raise SetupIncompleteError(
                'The metafields do not appear to have been set on {}. '
                'Does it inherit from ToggledWidgetFormMixin?'.format(form.__name__)
            )

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(deepcopy(super().get_fieldsets(request, obj)))
        fieldset_index = {}
        fields = set()
        for fieldset in fieldsets:
            for field_name in fieldset[1]['fields']:
                fieldset_index[field_name] = fieldset
                fields.add(field_name)
        form = self._get_form_for_get_fields(request, obj)
        try:
            for group in form.toggle_groups:
                field_names = [member[0] for member in group]
                metafield = form._metafield_index[field_names[0]]
                if metafield not in fields:
                    try:
                        fieldset = fieldset_index[field_names[0]]
                        fieldset[1]['fields'] = list(fieldset[1]['fields'])
                        self._insert_metafield(
                            fieldset[1]['fields'], metafield, field_names
                        )
                    except KeyError:
                        # The field must have been removed from the fieldset.
                        # Be agnostic about the validity of that.
                        pass
        except AttributeError:
            raise SetupIncompleteError(
                'The metafields do not appear to have been set on {}. '
                'Does it inherit from ToggledWidgetFormMixin, and does it '
                'define the toggle_groups attribute?'.format(self.form.__name__)
            )
        return fieldsets
