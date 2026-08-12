import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { finalize } from 'rxjs';

import { Holding, PortfolioApiService } from '../../core/services/portfolio-api.service';

@Component({
  selector: 'app-holdings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './holdings.component.html',
  styleUrl: './holdings.component.scss',
})
export class HoldingsComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  holdings: Holding[] = [];

  loading = true;
  error = '';

  totalInvested = 0;
  totalCurrentValue = 0;
  totalPnl = 0;
  totalPnlPercentage = 0;

  ngOnInit(): void {
    this.loadHoldings();
  }

  loadHoldings(): void {
    this.loading = true;
    this.error = '';

    this.portfolioApi
      .getHoldings()
      .pipe(
        finalize(() => {
          console.log('Holdings loading finished');

          this.loading = false;

          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: (data) => {
          console.log('Holdings API response:', data);

          this.holdings = data.results ?? [];

          this.calculateSummary();

          console.log('Holdings:', this.holdings);
          console.log('Holdings summary:', {
            totalInvested: this.totalInvested,
            totalCurrentValue: this.totalCurrentValue,
            totalPnl: this.totalPnl,
            totalPnlPercentage: this.totalPnlPercentage,
          });
        },

        error: (error) => {
          console.error('Holdings API error:', error);

          if (error?.status === 401 || error?.status === 403) {
            this.error = 'Authentication failed. Please log out and log in again.';
          } else if (error?.status === 0) {
            this.error =
              'Cannot connect to the Django backend. Make sure the backend is running on http://localhost:8000.';
          } else {
            this.error = `Unable to load holdings. Server returned ${
              error?.status ?? 'an unknown error'
            }.`;
          }
        },
      });
  }

  private calculateSummary(): void {
    this.totalInvested = this.holdings.reduce(
      (total, holding) => total + Number(holding.invested_value || 0),
      0,
    );

    this.totalCurrentValue = this.holdings.reduce(
      (total, holding) => total + Number(holding.current_value || 0),
      0,
    );

    this.totalPnl = this.totalCurrentValue - this.totalInvested;

    this.totalPnlPercentage =
      this.totalInvested > 0 ? (this.totalPnl / this.totalInvested) * 100 : 0;
  }

  refresh(): void {
    this.loadHoldings();
  }

  trackByHolding(_index: number, holding: Holding): number {
    return holding.id;
  }
}
