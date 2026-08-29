import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import { CommonModule } from '@angular/common';

import { WealthApiService } from '../../core/services/wealth-api.service';

export interface CreditRatingRow {
  credit_rating: string;
  current_value: number;
  percentage: number;
}

export interface FixedIncomeAnalysisResponse {
  current_value: number;
  number_of_holdings: number;
  ytm: number | null;
  ytm_holding_count: number;
  modified_duration: number | null;
  modified_duration_holding_count: number;
  average_maturity: number | null;
  average_maturity_holding_count: number;
  credit_rating_distribution: CreditRatingRow[];
}

/**
 * FIXED INCOME ANALYSIS
 *
 * Sourced from /api/analytics/wealth/fixed-income-analysis/ (see
 * InvestmentSummaryService.calculate_fixed_income_analysis).
 * Restricted to holdings classified under the Fixed Income
 * canonical asset category (the same classification the Dashboard
 * Investment Summary already uses), so "Current Value" here always
 * reconciles with that table's Fixed Income row.
 *
 * Same weighted-average-with-explicit-denominator approach as
 * Equity Analysis — see that component's doc comment.
 *
 * NOT built here: issuer concentration (Top 10 issuers — needs an
 * issuer/ISIN rollup, a reasonable follow-up on the same pattern as
 * Composition's AMC rollup), maturity-bucket chart (derivable from
 * average_maturity client-side, not yet wired up).
 */
@Component({
  selector: 'app-fixed-income-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './fixed-income-analysis.component.html',
  styleUrl: './fixed-income-analysis.component.scss',
})
export class FixedIncomeAnalysisComponent implements OnInit {
  private readonly wealthApi = inject(WealthApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  loading = true;
  error = '';

  analysis: FixedIncomeAnalysisResponse | null = null;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';

    this.wealthApi.getFixedIncomeAnalysis().subscribe({
      next: (data: FixedIncomeAnalysisResponse) => {
        this.analysis = data;
        this.loading = false;
        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('FIXED INCOME ANALYSIS API ERROR:', error);

        this.loading = false;
        this.error = 'Unable to load fixed income analysis.';
        this.cdr.markForCheck();
      },
    });
  }

  get hasData(): boolean {
    return (this.analysis?.number_of_holdings ?? 0) > 0;
  }

  formatCurrency(value: number): string {
    return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  }

  formatRatio(value: number | null, suffix = ''): string {
    return value === null ? '—' : `${value.toFixed(2)}${suffix}`;
  }

  formatPercentage(value: number): string {
    return `${value.toFixed(2)}%`;
  }
}
