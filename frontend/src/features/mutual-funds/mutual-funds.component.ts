import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { finalize, forkJoin } from 'rxjs';

import {
  MutualFundHolding,
  MutualFundSummary,
  MutualFundTransaction,
  MutualFundsApiService,
} from '../../core/services/mutual-funds-api.service';

@Component({
  selector: 'app-mutual-funds',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './mutual-funds.component.html',
  styleUrl: './mutual-funds.component.scss',
})
export class MutualFundsComponent implements OnInit {
  private readonly mutualFundsApi = inject(MutualFundsApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  summary: MutualFundSummary = {
    total_invested: 0,
    total_current_value: 0,
    total_unrealized_pnl: 0,
    pnl_percentage: 0,
    number_of_holdings: 0,
  };

  holdings: MutualFundHolding[] = [];
  transactions: MutualFundTransaction[] = [];

  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadMutualFunds();
  }

  loadMutualFunds(): void {
    this.loading = true;
    this.error = '';

    forkJoin({
      summary: this.mutualFundsApi.getSummary(),
      holdings: this.mutualFundsApi.getHoldings(),
      transactions: this.mutualFundsApi.getTransactions(),
    })
      .pipe(
        finalize(() => {
          console.log('Mutual Funds loading finished');

          this.loading = false;

          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: (data) => {
          console.log('Mutual Funds API response:', data);

          this.summary = data.summary;

          this.holdings = data.holdings.results ?? [];

          this.transactions = data.transactions.results ?? [];

          console.log('Mutual Fund summary:', this.summary);
          console.log('Mutual Fund holdings:', this.holdings);
          console.log('Mutual Fund transactions:', this.transactions);
        },

        error: (error) => {
          console.error('Mutual Funds API error:', error);

          if (error?.status === 401 || error?.status === 403) {
            this.error = 'Authentication failed. Please log out and log in again.';
          } else if (error?.status === 0) {
            this.error =
              'Cannot connect to the Django backend. Make sure the backend is running on http://localhost:8000.';
          } else {
            this.error = `Unable to load mutual funds. Server returned ${
              error?.status ?? 'an unknown error'
            }.`;
          }
        },
      });
  }

  refresh(): void {
    this.loadMutualFunds();
  }

  trackByHolding(_index: number, holding: MutualFundHolding): number {
    return holding.id;
  }

  trackByTransaction(_index: number, transaction: MutualFundTransaction): number {
    return transaction.id;
  }
}
