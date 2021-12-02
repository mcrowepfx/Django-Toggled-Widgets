class DjangoAdminFieldContext {
    constructor(field) {
        this.field = field;
    }

    get row() {
        if (this.field._row === undefined) {
            let element = this.field;
            while (element.parentElement) {
                let className = element.parentElement.getAttribute('class');
                if (className && className.indexOf('form-row') > -1) {
                    this.field._row = element.parentElement;
                    break;
                }
                element = element.parentElement;
            }
        }
        return this.field._row;
    }

    get fieldset() {
        if (this.field._fieldset === undefined) {
            let element = this.field;
            while (element.parentElement) {
                if (element.parentElement.tagName == 'FIELDSET') {
                    this.field._fieldset = element.parentElement;
                    break;
                }
                element = element.parentElement;
            }
        }
        return this.field._fieldset;
    }

    get prefix() {
        if (this._prefix === undefined) {
            let element = this.field;
            while (element.parentElement) {
                if (element.parentElement.tagName == 'FORM') {
                    // This field has no prefix
                    this._prefix = null;
                    break;
                }
                let className = element.parentElement.getAttribute('class');
                if (className && className.indexOf('inline-related') > -1) {
                    this._prefix = element.parentElement.id;
                    break;
                }
                element = element.parentElement;
            }
        }
        return this._prefix;
    }

    /* Finds a field within the wrapped field's fieldset with the given name,
    adding the appropriate prefix where necessary. */
    getSibling(name) {
        if (this.prefix) {
            name = this.prefix + '-' + name;
        }
        let fieldset = this.fieldset;
        if (fieldset) {
            return fieldset.querySelector('[name=' + name + ']');
        }
    }

    getBareFieldName() {
        let name = this.field.getAttribute('name');
        if (!this.prefix) {
            return name;
        }
        return name.substr(this.prefix.length + 1);
    }
}