import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { finalize, forkJoin } from 'rxjs';

import { DueSIP, SIP, SIPSummary, SipApiService } from '../../core/services/sip-api.service';

@Component({
  selector: 'app-sips',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sips.component.html',
  styleUrl: './sips.component.scss',
})
export class SipsComponent implements OnInit {
  private readonly sipApi = inject(SipApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  summary: SIPSummary = {
    total_sips: 0,
    active_sips: 0,
    total_monthly_commitment: 0,

    installments: {
      scheduled: 0,
      executed: 0,
      due: 0,
      skipped: 0,
      failed: 0,
    },

    actual_sip_invested: 0,
    pending_sip_amount: 0,

    next_installment: null,
  };

  sips: SIP[] = [];
  dueSips: DueSIP[] = [];

  loading = true;
  error = '';

  executingInstallmentId: number | null = null;

  ngOnInit(): void {
    this.loadSips();
  }

  loadSips(): void {
    this.loading = true;
    this.error = '';

    forkJoin({
      summary: this.sipApi.getSummary(),
      sips: this.sipApi.getSips(),
      dueSips: this.sipApi.getDueSips(),
    })
      .pipe(
        finalize(() => {
          console.log('SIP loading finished');

          this.loading = false;

          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: (data) => {
          console.log('SIP API response:', data);

          this.summary = data.summary;
          this.sips = data.sips.results ?? [];
          this.dueSips = data.dueSips.results ?? [];

          console.log('SIP summary:', this.summary);
          console.log('SIPs:', this.sips);
          console.log('Due SIPs:', this.dueSips);
        },

        error: (error) => {
          console.error('SIP API error:', error);

          if (error?.status === 401 || error?.status === 403) {
            this.error = 'Authentication failed. Please log out and log in again.';
          } else if (error?.status === 0) {
            this.error =
              'Cannot connect to the Django backend. Make sure the backend is running on http://localhost:8000.';
          } else {
            this.error = `Unable to load SIP data. Server returned ${
              error?.status ?? 'an unknown error'
            }.`;
          }
        },
      });
  }

  refresh(): void {
    this.loadSips();
  }

  executeInstallment(installmentId: number): void {
    if (this.executingInstallmentId !== null) {
      return;
    }

    const confirmed = window.confirm('Execute this SIP installment now?');

    if (!confirmed) {
      return;
    }

    this.executingInstallmentId = installmentId;

    this.sipApi
      .executeInstallment(installmentId)
      .pipe(
        finalize(() => {
          this.executingInstallmentId = null;

          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: (response) => {
          console.log('SIP installment executed:', response);

          this.loadSips();
        },

        error: (error) => {
          console.error('SIP installment execution failed:', error);

          const message = error?.error?.error ?? 'Unable to execute the SIP installment.';

          window.alert(message);
        },
      });
  }

  trackBySip(_index: number, sip: SIP): number {
    return sip.id;
  }

  trackByDueSip(_index: number, sip: DueSIP): number {
    return sip.id;
  }

  getStatusClass(status: string): string {
    return status.toLowerCase();
  }
}
