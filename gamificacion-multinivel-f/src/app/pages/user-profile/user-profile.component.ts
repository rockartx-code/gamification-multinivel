import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { finalize } from 'rxjs';

import { CustomerDocumentTypeConfig, CustomerProfile } from '../../models/admin.model';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';

interface OwnDocUploadState {
  file: File | null;
  uploading: boolean;
  error: string;
}

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent],
  templateUrl: './user-profile.component.html'
})
export class UserProfileComponent implements OnInit {
  previewDoc: { name: string; url?: string; type?: string; uploadedAt?: string } | null = null;
  previewSafeUrl: SafeResourceUrl | null = null;

  constructor(
    private readonly api: ApiService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef,
    private readonly sanitizer: DomSanitizer
  ) {}

  isLoading = true;
  isSavingInfo = false;
  isSavingClabe = false;
  toastMessage = '';
  isToastVisible = false;
  private toastTimeout?: number;

  profile: CustomerProfile | null = null;

  infoForm = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', phone: '', rfc: '', curp: '' };
  clabeDraft = '';
  bankInstitutionDraft = '';
  clabePending = '';
  isClabeConfirmOpen = false;

  passwordForm = { currentPassword: '', newPassword: '', confirmPassword: '' };
  passwordErrors = { currentPassword: '', newPassword: '', confirmPassword: '' };
  isSavingPassword = false;
  showCurrentPassword = false;
  showNewPassword = false;
  showConfirmPassword = false;

  // Customer own document upload
  requiredDocTypes: CustomerDocumentTypeConfig[] = [];
  ownDocStates: Record<string, OwnDocUploadState> = {};

  ngOnInit(): void {
    const user = this.authService.currentUser;
    if (!user?.userId) {
      void this.router.navigate(['/dashboard']);
      return;
    }

    // Load profile and business config in parallel
    this.api.getCustomer(user.userId)
      .pipe(finalize(() => { this.isLoading = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (profile) => {
          this.profile = profile;
          const nameParts = this.splitStoredName(profile.name || '');
          this.infoForm = {
            firstName: nameParts.firstName,
            apellidoPaterno: nameParts.apellidoPaterno,
            apellidoMaterno: nameParts.apellidoMaterno,
            phone: profile.phone || '',
            rfc: profile.rfc || '',
            curp: profile.curp || ''
          };
          this.clabeDraft = profile.clabeInterbancaria || '';
          this.bankInstitutionDraft = profile.bankInstitution || '';
          this.cdr.markForCheck();
        },
        error: () => { this.showToast('No se pudo cargar el perfil.'); }
      });

    this.api.getBusinessConfig().subscribe({
      next: (config) => {
        const types = config.customerDocumentTypes ?? this.defaultDocumentTypes();
        this.requiredDocTypes = types;
        this.ownDocStates = {};
        for (const dt of types) {
          this.ownDocStates[dt.key] = { file: null, uploading: false, error: '' };
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.requiredDocTypes = this.defaultDocumentTypes();
        for (const dt of this.requiredDocTypes) {
          this.ownDocStates[dt.key] = { file: null, uploading: false, error: '' };
        }
        this.cdr.markForCheck();
      }
    });
  }

  get userId(): string {
    return this.authService.currentUser?.userId ?? '';
  }

  get maskedClabe(): string {
    const clabe = this.profile?.clabeInterbancaria || '';
    if (!clabe) return '';
    return '•••• •••• •••• ' + clabe.slice(-4);
  }

  saveInfo(): void {
    if (this.isSavingInfo || !this.userId) return;
    this.isSavingInfo = true;
    const fullName = `${this.infoForm.firstName.trim()} ${this.infoForm.apellidoPaterno.trim()} ${this.infoForm.apellidoMaterno.trim()}`.trim();
    this.api.updateProfile(this.userId, {
      name: fullName,
      phone: this.infoForm.phone.trim(),
      rfc: this.infoForm.rfc.trim().toUpperCase(),
      curp: this.infoForm.curp.trim().toUpperCase()
    }).pipe(finalize(() => { this.isSavingInfo = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (updated) => {
          this.profile = { ...this.profile!, ...updated };
          this.showToast('Información guardada correctamente.');
        },
        error: () => { this.showToast('No se pudo guardar la información.'); }
      });
  }

  openClabeConfirm(): void {
    const clean = this.clabeDraft.replace(/\s/g, '');
    if (clean.length !== 18) {
      this.showToast('La CLABE debe tener 18 dígitos.');
      return;
    }
    this.clabePending = clean;
    this.isClabeConfirmOpen = true;
  }

  cancelClabeConfirm(): void {
    this.isClabeConfirmOpen = false;
    this.clabePending = '';
  }

  confirmSaveClabe(): void {
    if (this.isSavingClabe || !this.userId) return;
    this.isClabeConfirmOpen = false;
    this.isSavingClabe = true;
    const customerId = Number(this.userId);
    this.api.saveCustomerClabe({
      customerId,
      clabe: this.clabePending,
      bankInstitution: this.bankInstitutionDraft.trim() || undefined
    })
      .pipe(finalize(() => { this.isSavingClabe = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (res) => {
          if (this.profile) {
            this.profile = {
              ...this.profile,
              clabeInterbancaria: this.clabePending,
              clabeLast4: res.clabeLast4 ?? this.clabePending.slice(-4),
              bankInstitution: this.bankInstitutionDraft.trim() || this.profile.bankInstitution
            };
          }
          this.clabeDraft = this.clabePending;
          this.clabePending = '';
          this.showToast('CLABE guardada correctamente.');
        },
        error: () => { this.showToast('No se pudo guardar la CLABE.'); }
      });
  }

  onOwnDocFileChange(docKey: string, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    if (this.ownDocStates[docKey]) {
      this.ownDocStates[docKey] = { ...this.ownDocStates[docKey], file, error: '' };
    }
  }

  uploadOwnDoc(docType: CustomerDocumentTypeConfig): void {
    const state = this.ownDocStates[docType.key];
    if (!state?.file || state.uploading || !this.userId) return;

    this.ownDocStates[docType.key] = { ...state, uploading: true, error: '' };
    this.cdr.markForCheck();

    const reader = new FileReader();
    reader.onload = () => {
      const raw = reader.result as string;
      // raw = "data:<contentType>;base64,<data>"
      const [meta, contentBase64] = raw.split(',');
      const contentType = (meta?.match(/:(.*?);/) ?? [])[1] ?? 'application/octet-stream';

      this.api.uploadCustomerOwnDocument({
        userId: this.userId,
        docType: docType.key,
        docLabel: docType.label,
        contentBase64: contentBase64 ?? '',
        contentType,
        fileName: state.file!.name
      }).pipe(finalize(() => {
        this.ownDocStates[docType.key] = { ...this.ownDocStates[docType.key], uploading: false };
        this.cdr.markForCheck();
      })).subscribe({
        next: (updated) => {
          this.profile = { ...this.profile!, ownDocuments: updated.ownDocuments };
          this.ownDocStates[docType.key] = { file: null, uploading: false, error: '' };
          this.showToast(`${docType.label} subido correctamente.`);
        },
        error: () => {
          this.ownDocStates[docType.key] = { ...this.ownDocStates[docType.key], error: 'No se pudo subir el documento.' };
          this.showToast('No se pudo subir el documento.');
        }
      });
    };
    reader.onerror = () => {
      this.ownDocStates[docType.key] = { ...state, uploading: false, error: 'Error al leer el archivo.' };
      this.cdr.markForCheck();
    };
    reader.readAsDataURL(state.file);
  }

  getOwnDocForType(docKey: string): { name: string; uploadedAt?: string; url?: string; type?: string } | null {
    return (this.profile?.ownDocuments ?? []).find((d) => d.docType === docKey) ?? null;
  }

  isPdf(doc: { type?: string; url?: string }): boolean {
    const ct = (doc.type || '').toLowerCase();
    if (ct === 'application/pdf') return true;
    return (doc.url || '').toLowerCase().split('?')[0].endsWith('.pdf');
  }

  isImage(doc: { type?: string; url?: string }): boolean {
    const ct = (doc.type || '').toLowerCase();
    if (ct.startsWith('image/')) return true;
    return /\.(jpe?g|png|gif|webp|svg)(\?|$)/i.test(doc.url || '');
  }

  isPreviewable(doc: { type?: string; url?: string }): boolean {
    return this.isPdf(doc) || this.isImage(doc);
  }

  openPreview(doc: { name: string; url?: string; type?: string; uploadedAt?: string }): void {
    this.previewDoc = doc;
    this.previewSafeUrl = doc.url
      ? this.sanitizer.bypassSecurityTrustResourceUrl(doc.url)
      : null;
  }

  closePreview(): void {
    this.previewDoc = null;
    this.previewSafeUrl = null;
  }

  changePassword(): void {
    this.passwordErrors = { currentPassword: '', newPassword: '', confirmPassword: '' };
    if (!this.passwordForm.currentPassword) {
      this.passwordErrors.currentPassword = 'Ingresa tu contraseña actual.';
    }
    if (!this.passwordForm.newPassword || this.passwordForm.newPassword.length < 8) {
      this.passwordErrors.newPassword = 'La nueva contraseña debe tener al menos 8 caracteres.';
    }
    if (!this.passwordForm.confirmPassword) {
      this.passwordErrors.confirmPassword = 'Confirma la nueva contraseña.';
    } else if (this.passwordForm.newPassword !== this.passwordForm.confirmPassword) {
      this.passwordErrors.confirmPassword = 'Las contraseñas no coinciden.';
    }
    if (this.passwordErrors.currentPassword || this.passwordErrors.newPassword || this.passwordErrors.confirmPassword) {
      return;
    }
    if (this.isSavingPassword || !this.userId) return;
    this.isSavingPassword = true;
    this.api.changePassword(this.userId, {
      currentPassword: this.passwordForm.currentPassword,
      newPassword: this.passwordForm.newPassword
    }).pipe(finalize(() => { this.isSavingPassword = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: () => {
          this.passwordForm = { currentPassword: '', newPassword: '', confirmPassword: '' };
          this.showCurrentPassword = false;
          this.showNewPassword = false;
          this.showConfirmPassword = false;
          this.showToast('Contraseña actualizada correctamente.');
        },
        error: (err: any) => {
          const msg = err?.error?.message || 'No se pudo actualizar la contraseña.';
          this.showToast(msg);
        }
      });
  }

  formatDate(iso?: string): string {
    if (!iso) return '-';
    return new Date(iso).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private defaultDocumentTypes(): CustomerDocumentTypeConfig[] {
    return [
      { key: 'constancia', label: 'Constancia de situación fiscal', required: true },
      { key: 'ine', label: 'INE (frente y reverso)', required: true },
      { key: 'curp', label: 'CURP', required: true }
    ];
  }

  private splitStoredName(name: string): { firstName: string; apellidoPaterno: string; apellidoMaterno: string } {
    const words = name.trim().split(/\s+/).filter(w => w.length > 0);
    if (words.length === 0) return { firstName: '', apellidoPaterno: '', apellidoMaterno: '' };
    if (words.length === 1) return { firstName: words[0], apellidoPaterno: '', apellidoMaterno: '' };
    if (words.length === 2) return { firstName: words[0], apellidoPaterno: words[1], apellidoMaterno: '' };
    if (words.length === 3) return { firstName: words[0], apellidoPaterno: words[1], apellidoMaterno: words[2] };
    return {
      firstName: words.slice(0, words.length - 2).join(' '),
      apellidoPaterno: words[words.length - 2],
      apellidoMaterno: words[words.length - 1]
    };
  }

  private showToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    if (this.toastTimeout) window.clearTimeout(this.toastTimeout);
    this.toastTimeout = window.setTimeout(() => {
      this.isToastVisible = false;
      this.cdr.markForCheck();
    }, 2500);
  }
}
