import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})
export class LandingComponent implements OnInit {
  readonly currentYear = new Date().getFullYear();

  form = {
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };

  referralToken = '';
  productId = '';
  isSubmitting = false;
  feedbackMessage = '';
  feedbackType: 'error' | 'success' | '' = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('refToken') ?? '';
    const product = this.route.snapshot.queryParamMap.get('p') ?? '';
    this.referralToken = token.trim();
    this.productId = product.trim();
  }

  scrollTo(sectionId: string, event?: Event): void {
    event?.preventDefault();
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  createAccount(): void {
    if (this.isSubmitting) {
      return;
    }
    if (!this.form.name || !this.form.email || !this.form.password) {
      this.setFeedback('Completa los campos obligatorios.', 'error');
      return;
    }
    if (this.form.password !== this.form.confirmPassword) {
      this.setFeedback('Las contraseñas no coinciden.', 'error');
      return;
    }

    const payload = {
      name: this.form.name.trim(),
      email: this.form.email.trim(),
      phone: this.form.phone.trim() || undefined,
      password: this.form.password,
      confirmPassword: this.form.confirmPassword,
      referralToken: this.referralToken || undefined,
      productId: this.productId || undefined
    };

    this.isSubmitting = true;
    this.api
      .createAccount(payload)
      .pipe(
        finalize(() => {
          this.isSubmitting = false;
        })
      )
      .subscribe({
        next: () => {
          this.form = { name: '', email: '', phone: '', password: '', confirmPassword: '' };
          this.setFeedback('Cuenta creada. Revisa tu correo para continuar.', 'success');
        },
        error: (error: Error) => {
          this.setFeedback(error.message || 'No se pudo crear la cuenta.', 'error');
        }
      });
  }

  private setFeedback(message: string, type: 'error' | 'success'): void {
    this.feedbackMessage = message;
    this.feedbackType = type;
  }
}
