import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterLink, UiButtonComponent],
  templateUrl: './verify-email.component.html'
})
export class VerifyEmailComponent implements OnInit {
  state: 'loading' | 'success' | 'error' | 'no-token' = 'loading';
  message = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token')?.trim() ?? '';
    if (!token) {
      this.state = 'no-token';
      this.cdr.markForCheck();
      return;
    }
    this.api.verifyEmail(token)
      .pipe(finalize(() => this.cdr.markForCheck()))
      .subscribe({
        next: () => {
          this.state = 'success';
        },
        error: (err: any) => {
          this.state = 'error';
          this.message = err?.error?.message || 'El enlace es inválido o ya expiró.';
        }
      });
  }
}
