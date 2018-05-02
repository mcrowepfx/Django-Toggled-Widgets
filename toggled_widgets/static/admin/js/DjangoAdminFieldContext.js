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
}