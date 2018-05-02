from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.forms import CharField
from django.forms.models import ModelFormMetaclass
from django.forms.widgets import HiddenInput, Widget
from django.utils import six
    
class SetupIncompleteError(Exception):
    pass

class ToggledWidget(Widget):
    """
    Widgets inheriting from this class have behavior that allows them to be
    paired with another instance descending from the same class to enable
    visibility to be toggled between the two.
    """
    toggle_button_text = 'Toggle'
    
    class Media:
        js = ('admin/js/DjangoAdminFieldContext.js', 'admin/js/toggledWidgets.js')
        
    def __init__(self, *args, **kwargs):
        super(ToggledWidget, self).__init__(*args, **kwargs)
        self.paired_widget = None
        # Cohorts are other Widget instances (of any type) that are meant to
        # be toggled along with this one.
        self.cohorts = None
        self.pairing_id = id(self)
        self.visible = True
        
    def __deepcopy__(self, memo):
        """
        Ensures that the copy and its cohorts get a new pairing ID.
        """
        copied = super(ToggledWidget, self).__deepcopy__(memo)
        copied.pairing_id = id(copied)
        copied.sync_cohorts()
        return copied
        
    def set_paired_widget(self, paired):
        if not isinstance(paired, ToggledWidget):
            raise TypeError('The paired widget must inherit from ToggledWidget.')
        self.paired_widget = paired
        self.paired_widget.set_metafield_name(self.attrs['data-metafield-name'])
        paired.paired_widget = self
        
    def set_cohorts(self, cohorts):
        self.cohorts = cohorts
        self.sync_cohorts()
            
    def sync_cohorts(self):
        if self.cohorts:
            for cohort in self.cohorts:
                # This drove me nuts for hours: widgets for choice fields in
                # the admin are wrapped in a containing widget, which meant
                # that for such fields, this code was setting this extra
                # attribute on the wrong object.
                attrs = cohort.widget.attrs if isinstance(cohort, RelatedFieldWidgetWrapper) else cohort.attrs
                attrs['data-master-toggle-id'] = self.pairing_id
        
    def set_metafield_name(self, metafield_name):
        """
        Sets the name of a hidden field that's part of the same fieldset as the
        field that owns this widget. This field will be set to the name of the
        field that is visible at any given time so the back end can know which
        of the two fields to use and which to discard.
        """
        self.attrs['data-metafield-name'] = metafield_name
        
    def toggle_visibility(self):
        if not self.paired_widget:
            raise SetupIncompleteError('Cannot toggle visibility on an unpaired widget.')
        original = self.visible
        self.visible = not original
        self.paired_widget.visible = not self.visible
        
    def set_visible(self):
        if not self.visible:
            self.toggle_visibility()
        
    def build_attrs(self, *args, **kwargs):
        attrs = super(ToggledWidget, self).build_attrs(*args, **kwargs)
        if self.paired_widget:
            attrs.update({
                'data-toggle-id': self.pairing_id,
                'data-toggle-pairing': self.paired_widget.pairing_id,
                'data-toggle-button-text': self.toggle_button_text,
                'data-visible': '1' if self.visible else ''
            })
        return attrs
        
class ToggledWidgetModelFormMetaclass(ModelFormMetaclass):
    """
    Metaclass that adds class-level hidden metafield attributes for each
    toggled field pair, which is necessary for the field to appear in the
    rendered form.
    """
    def __new__(cls, name, bases, attrs):
        for pair in attrs.get('toggle_pairs', ()):
            master_field = ToggledWidgetFormMixin.split_pairing_member(pair[0])[0]
            attrs[ToggledWidgetFormMixin.build_metafield_name(master_field)] = CharField(
                widget=HiddenInput
            )
        return super(ToggledWidgetModelFormMetaclass, cls).__new__(cls, name, bases, attrs)
        
class ToggledWidgetFormMixin(six.with_metaclass(ToggledWidgetModelFormMetaclass)):
    """
    Provides special handling for the initialization and submission of forms
    containing toggled widgets.
    """
    toggle_pairs = []
    
    def __init__(self, *args, **kwargs):
        super(ToggledWidgetFormMixin, self).__init__(*args, **kwargs)
        self.resolved_toggle_pairs = self.get_resolved_toggle_pairs()
        self.cohort_fields_index = {}
        for master, paired in self.resolved_toggle_pairs:
            metafield_name = self.build_metafield_name(master[0])
            master_widget = self.fields[master[0]].widget
            paired_widget = self.fields[paired[0]].widget
            master_widget.set_metafield_name(metafield_name)
            cohorts = []
            for field in master[1]:
                self.cohort_fields_index[field] = master[0]
                cohorts.append(self.fields[field].widget)
            master_widget.set_cohorts(cohorts)
            master_widget.set_paired_widget(paired_widget)
            cohorts = []
            for field in paired[1]:
                self.cohort_fields_index[field] = paired[0]
                cohorts.append(self.fields[field].widget)
            paired_widget.set_cohorts(cohorts)
            # As the initial value of the metafield, we'll use the master
            # field name, unless the instance attribute corresponding with the
            # paired field name has a value.
            if getattr(self.instance, paired[0], None):
                metafield_initial = paired[0]
                # Toggle visibility on the other widget
                master_widget.toggle_visibility()
            else:
                metafield_initial = master[0]
                paired_widget.toggle_visibility()
            self.fields[metafield_name].initial = metafield_initial
        
    @staticmethod
    def build_metafield_name(field_name):
        return '{}_metafield'.format(field_name)
        
    @staticmethod
    def split_pairing_member(member):
        """
        Helper method for dealing with the fact that either member of a
        toggled widget pairing may be either a single field name or a list-
        like object containing multiple field names, the first of which
        controls the toggling behavior and the remainder of which toggle
        sympathetically.
        """
        if isinstance(member, six.text_type):
            return (member, ())
        try:
            return (member[0], member[1:])
        except (KeyError, TypeError):
            raise TypeError(
                'Members of widget pairings must either be strings or list-'
                'like objects containing more than one stirng.'
            )
    
    @classmethod        
    def get_resolved_toggle_pairs(cls):
        resolved = []
        for pair in cls.toggle_pairs:
            master_field, master_cohorts = cls.split_pairing_member(pair[0])
            paired_field, paired_cohorts = cls.split_pairing_member(pair[1])
            resolved.append(
                ((master_field, master_cohorts), (paired_field, paired_cohorts))
            )
        return resolved
        
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
                field_instance = self.fields[self.cohort_fields_index[field]]
            except KeyError:
                if not isinstance(self.fields[field].widget, ToggledWidget):
                    return
                field_instance = self.fields[field]
            if not field_instance.widget.visible:
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