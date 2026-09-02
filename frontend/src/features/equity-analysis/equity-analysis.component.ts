import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import { CommonModule } from '@angular/common';

import { WealthApiService } from '../../core/services/wealth-api.service';

export interface MarketCapRow {
  cap_type: string;
  current_value: number;
  percentage: number;
}

export interface EquityAnalysisResponse {
  current_value: number;
  number_of_holdings: number;
  portfolio_pe: number | null;
  portfolio_pe_holding_count: number;
  portfolio_pb: number | null;
  portfolio_pb_holding_count: number;
  portfolio_roe: number | null;
  portfolio_roe_holding_count: number;
  market_cap_allocation: MarketCapRow[];
}

/**
 * EQUITY ANALYSIS
 *
 * Sourced from /api/analytics/wealth/equity-analysis/ (see
 * InvestmentSummaryService.calculate_equity_analysis). Every quant
 * figure here (P/E, P/B, ROE) is a value-weighted average computed
 * ONLY over holdings that have SecurityMaster data populated for
 * that specific field — the holding_count next to each figure is
 * the real denominator, shown explicitly rather than hidden, since
 * with SecurityMaster still sparsely populated a "portfolio P/E"
 * silently based on 1 of 40 holdings would be misleading without it.
 *
 * NOT built here (still open, same reasons noted throughout this
 * conversation): sector allocation vs benchmark, forward P/E / P/B,
 * top-stocks-by-exposure table, product-category performance
 * (needs benchmark IRR, which is unbuilt).
 */
@Component({
  selector: 'app-equity-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './equity-analysis.component.html',
  styleUrl: './equity-analysis.component.scss',
})
export class EquityAnalysisComponent implements OnInit {
  private readonly wealthApi = inject(WealthApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  loading = true;
  error = '';

  analysis: EquityAnalysisResponse | null = null;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';

    this.wealthApi.getEquityAnalysis().subscribe({
      next: (data: EquityAnalysisResponse) => {
        this.analysis = data;
        this.loading = false;
        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('EQUITY ANALYSIS API ERROR:', error);

        this.loading = false;
        this.error = 'Unable to load equity analysis.';
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

  formatRatio(value: number | null): string {
    return value === null ? '—' : value.toFixed(2);
  }

  formatPercentage(value: number): string {
    return `${value.toFixed(2)}%`;
  }
}
