import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { CustomerDocument, CustomerProfile } from '../../models/admin.model';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent],
  templateUrl: './user-profile.component.html'
})
export class UserProfileComponent implements OnInit {
  constructor(
    private readonly api: ApiService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  isLoading = true;
  isSavingInfo = false;
  isSavingClabe = false;
  isUploadingDoc = false;

  toastMessage = '';
  isToastVisible = false;
  private toastTimeout?: number;

  profile: CustomerProfile | null = null;

  infoForm = { name: '', phone: '', rfc: '', curp: '' };
  clabeDraft = '';
  clabePending = '';
  isClabeConfirmOpen = false;

  selectedDocFile: File | null = null;
  selectedDocName = '';

  passwordForm = { currentPassword: '', newPassword: '', confirmPassword: '' };
  passwordErrors = { currentPassword: '', newPassword: '', confirmPassword: '' };
  isSavingPassword = false;
  showCurrentPassword = false;
  showNewPassword = false;
  showConfirmPassword = false;

  ngOnInit(): void {
    const user = this.authService.currentUser;
    if (!user?.userId) {
      void this.router.navigate(['/dashboard']);
      return;
    }
    this.api.getCustomer(user.userId).pipe(finalize(() => { this.isLoading = false; this.cdr.markForCheck(); })).subscribe({
      next: (profile) => {
        this.profile = profile;
        this.infoForm = {
          name: profile.name || '',
          phone: profile.phone || '',
          rfc: profile.rfc || '',
          curp: profile.curp || ''
        };
        this.clabeDraft = profile.clabeInterbancaria || '';
        this.cdr.markForCheck();
      },
      error: () => { this.showToast('No se pudo cargar el perfil.'); }
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
    this.api.updateProfile(this.userId, {
      name: this.infoForm.name.trim(),
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
    this.api.saveCustomerClabe({ customerId, clabe: this.clabePending })
      .pipe(finalize(() => { this.isSavingClabe = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (res) => {
          if (this.profile) {
            this.profile = {
              ...this.profile,
              clabeInterbancaria: this.clabePending,
              clabeLast4: res.clabeLast4 ?? this.clabePending.slice(-4)
            };
          }
          this.clabeDraft = this.clabePending;
          this.clabePending = '';
          this.showToast('CLABE guardada correctamente.');
        },
        error: () => { this.showToast('No se pudo guardar la CLABE.'); }
      });
  }

  onDocFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedDocFile = file;
    this.selectedDocName = file ? file.name.replace(/\.[^.]+$/, '') : '';
    this.cdr.markForCheck();
    input.value = '';
  }

  uploadDocument(): void {
    if (!this.selectedDocFile || this.isUploadingDoc) return;
    const name = (this.selectedDocName.trim() || this.selectedDocFile.name.replace(/\.[^.]+$/, '')).trim();
    const file = this.selectedDocFile;
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1] ?? '';
      this.isUploadingDoc = true;
      this.cdr.markForCheck();
      this.api.createAsset({ name, contentBase64: base64, contentType: file.type })
        .pipe(finalize(() => { this.isUploadingDoc = false; this.cdr.markForCheck(); }))
        .subscribe({
          next: (res) => {
            const doc: CustomerDocument = {
              id: res.asset.assetId,
              name,
              type: file.type,
              url: res.asset.url,
              uploadedAt: new Date().toISOString()
            };
            if (this.profile) {
              this.profile = { ...this.profile, documents: [...(this.profile.documents ?? []), doc] };
            }
            this.selectedDocFile = null;
            this.selectedDocName = '';
            this.showToast('Documento subido correctamente.');
          },
          error: () => { this.showToast('No se pudo subir el documento.'); }
        });
    };
    reader.readAsDataURL(file);
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
