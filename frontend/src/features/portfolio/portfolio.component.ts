import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { finalize, forkJoin } from 'rxjs';

import {
  Holding,
  PortfolioApiService,
  PortfolioSummary,
  Transaction,
} from '../../core/services/portfolio-api.service';

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss',
})
export class PortfolioComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  summary: PortfolioSummary | null = null;
  holdings: Holding[] = [];
  transactions: Transaction[] = [];

  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadPortfolio();
  }

  loadPortfolio(): void {
    this.loading = true;
    this.error = '';

    forkJoin({
      summary: this.portfolioApi.getSummary(),
      holdings: this.portfolioApi.getHoldings(),
      transactions: this.portfolioApi.getTransactions(),
    })
      .pipe(
        finalize(() => {
          console.log('Portfolio loading finished');

          this.loading = false;

          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: (data) => {
          console.log('Portfolio API response:', data);

          this.summary = data.summary;
          this.holdings = data.holdings?.results ?? [];
          this.transactions = data.transactions?.results ?? [];

          console.log('Portfolio summary:', this.summary);
          console.log('Portfolio holdings:', this.holdings);
          console.log('Portfolio transactions:', this.transactions);
        },

        error: (error) => {
          console.error('Portfolio API error:', error);

          if (error?.status === 401 || error?.status === 403) {
            this.error = 'Authentication failed. Please log out and log in again.';
          } else if (error?.status === 0) {
            this.error =
              'Cannot connect to the Django backend. Make sure the backend is running on http://localhost:8000.';
          } else {
            this.error = `Unable to load portfolio data. Server returned ${
              error?.status ?? 'an unknown error'
            }.`;
          }
        },
      });
  }

  refresh(): void {
    this.loadPortfolio();
  }

  trackByHolding(_index: number, holding: Holding): number {
    return holding.id;
  }

  trackByTransaction(_index: number, transaction: Transaction): number {
    return transaction.id;
  }
}
