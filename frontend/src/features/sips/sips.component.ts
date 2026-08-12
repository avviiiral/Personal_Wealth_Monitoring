import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { SipApiService, SIPSummary, SIP, DueSIP } from '../../core/services/sip-api.service';

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

  summary: SIPSummary | null = null;
  sips: SIP[] = [];
  dueSips: DueSIP[] = [];

  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.error = '';

    let completed = 0;

    const completeRequest = (): void => {
      completed++;

      if (completed === 3) {
        this.loading = false;
        this.cdr.detectChanges();
      }
    };

    this.sipApi.getSummary().subscribe({
      next: (data) => {
        this.summary = data;
        completeRequest();
      },

      error: (error) => {
        console.error('SIP summary error:', error);

        if (!this.error) {
          this.error = 'Unable to load SIP summary.';
        }

        completeRequest();
      },
    });

    this.sipApi.getSips().subscribe({
      next: (data) => {
        this.sips = data.results ?? [];
        completeRequest();
      },

      error: (error) => {
        console.error('SIP list error:', error);

        if (!this.error) {
          this.error = 'Unable to load SIPs.';
        }

        completeRequest();
      },
    });

    this.sipApi.getDueSips().subscribe({
      next: (data) => {
        this.dueSips = data.results ?? [];
        completeRequest();
      },

      error: (error) => {
        console.error('Due SIPs error:', error);

        if (!this.error) {
          this.error = 'Unable to load due SIPs.';
        }

        completeRequest();
      },
    });
  }

  refresh(): void {
    this.loadData();
  }

  formatCurrency(value: number | null | undefined): string {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(Number(value ?? 0));
  }

  formatNumber(value: number | null | undefined, maximumFractionDigits = 2): string {
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 0,
      maximumFractionDigits,
    }).format(Number(value ?? 0));
  }

  formatDate(value: string | null | undefined): string {
    if (!value) {
      return '—';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(date);
  }

  getStatusClass(status: string | null | undefined): string {
    return (status ?? 'unknown').toLowerCase().replace(/\s+/g, '-');
  }

  getFrequencyClass(frequency: string | null | undefined): string {
    return (frequency ?? 'unknown').toLowerCase().replace(/\s+/g, '-');
  }

  getDueLabel(dueCount: number): string {
    if (dueCount === 1) {
      return '1 installment due';
    }

    return `${dueCount} installments due`;
  }

  trackBySip(_index: number, sip: SIP): number {
    return sip.id;
  }

  trackByDueSip(_index: number, sip: DueSIP): number {
    return sip.id;
  }
}
