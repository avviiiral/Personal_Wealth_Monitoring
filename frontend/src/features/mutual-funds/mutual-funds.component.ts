import { AfterViewInit, ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import {
  MutualFundsApiService,
  MutualFundSummary,
  MutualFundHolding,
  MutualFundTransaction,
} from '../../core/services/mutual-funds-api.service';

@Component({
  selector: 'app-mutual-funds',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './mutual-funds.component.html',
  styleUrl: './mutual-funds.component.scss',
})
export class MutualFundsComponent implements OnInit, AfterViewInit {
  private readonly mutualFundsApi = inject(MutualFundsApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  summary: MutualFundSummary | null = null;
  holdings: MutualFundHolding[] = [];
  transactions: MutualFundTransaction[] = [];

  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadData();
  }

  ngAfterViewInit(): void {
    this.cdr.detectChanges();
  }

  loadData(): void {
    this.loading = true;
    this.error = '';

    let completed = 0;
    let failed = false;

    const completeRequest = (): void => {
      completed++;

      if (completed === 3) {
        this.loading = false;
        this.cdr.detectChanges();
      }
    };

    this.mutualFundsApi.getSummary().subscribe({
      next: (data) => {
        this.summary = data;
        completeRequest();
      },
      error: (error) => {
        console.error('Mutual fund summary error:', error);
        failed = true;
        this.error = 'Unable to load mutual fund summary.';
        completeRequest();
      },
    });

    this.mutualFundsApi.getHoldings().subscribe({
      next: (data) => {
        this.holdings = data.results ?? [];
        completeRequest();
      },
      error: (error) => {
        console.error('Mutual fund holdings error:', error);
        failed = true;

        if (!this.error) {
          this.error = 'Unable to load mutual fund holdings.';
        }

        completeRequest();
      },
    });

    this.mutualFundsApi.getTransactions().subscribe({
      next: (data) => {
        this.transactions = data.results ?? [];
        completeRequest();
      },
      error: (error) => {
        console.error('Mutual fund transactions error:', error);
        failed = true;

        if (!this.error) {
          this.error = 'Unable to load mutual fund transactions.';
        }

        completeRequest();
      },
    });
  }

  refresh(): void {
    this.loadData();
  }

  formatCurrency(value: number | null | undefined): string {
    const amount = Number(value ?? 0);

    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(amount);
  }

  formatNumber(value: number | null | undefined, maximumFractionDigits = 4): string {
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 0,
      maximumFractionDigits,
    }).format(Number(value ?? 0));
  }

  formatPercentage(value: number | null | undefined): string {
    return `${Number(value ?? 0).toFixed(2)}%`;
  }

  getPnlClass(value: number | null | undefined): string {
    const amount = Number(value ?? 0);

    if (amount > 0) {
      return 'positive';
    }

    if (amount < 0) {
      return 'negative';
    }

    return 'neutral';
  }

  getPnlIcon(value: number | null | undefined): string {
    const amount = Number(value ?? 0);

    if (amount > 0) {
      return '▲';
    }

    if (amount < 0) {
      return '▼';
    }

    return '—';
  }

  trackByHolding(_index: number, holding: MutualFundHolding): number {
    return holding.id;
  }

  trackByTransaction(_index: number, transaction: MutualFundTransaction): number {
    return transaction.id;
  }
}
