import { CommonModule } from '@angular/common';
import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';

type FieldOption = { value: string | number; label: string };

@Component({
  selector: 'ui-form-field',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ui-form-field.component.html',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => UiFormFieldComponent),
      multi: true
    }
  ]
})
export class UiFormFieldComponent implements ControlValueAccessor {
  @Input() kind: 'input' | 'textarea' | 'select' = 'input';
  @Input() type = 'text';
  @Input() label = '';
  @Input() placeholder = '';
  @Input() name = '';
  @Input() rows = 3;
  @Input() readonly = false;
  @Input() min: number | null = null;
  @Input() max: number | null = null;
  @Input() step: number | null = null;
  @Input() accept = '';
  @Input() iconClass = '';
  @Input() leadingIconClass = '';
  @Input() helpText = '';
  @Input() errorText = '';
  @Input() options: FieldOption[] = [];
  @Input() wrapperClass = 'block';
  @Input() inputClass =
    'mt-1 w-full rounded-2xl border border-olive-30 bg-white/70 px-3 py-2.5 text-sm text-main placeholder:text-muted focus:border-olive-70';

  value = '';
  disabled = false;

  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  writeValue(value: string | null): void {
    this.value = value ?? '';
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(disabled: boolean): void {
    this.disabled = disabled;
  }

  updateValue(value: string): void {
    this.value = value;
    this.onChange(value);
  }

  markTouched(): void {
    this.onTouched();
  }

  get hasError(): boolean {
    return Boolean(this.errorText);
  }

  get resolvedLeadingIconClass(): string {
    return this.leadingIconClass || (!this.label ? this.iconClass : '');
  }

  get inputStateClass(): string {
    const baseStateClass = this.hasError
      ? 'border-danger/70 focus:border-danger focus:ring-danger/20'
      : 'border-olive-30 focus:border-olive-70 focus-ring-olive-20';
    const iconPadding = this.resolvedLeadingIconClass ? 'pl-10' : '';
    return `${baseStateClass} ${iconPadding}`.trim();
  }
}
