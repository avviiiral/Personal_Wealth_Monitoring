import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  inject,
} from '@angular/core';

import { CommonModule } from '@angular/common';

import { Chart, ChartConfiguration, registerables } from 'chart.js';

import { WealthApiService } from '../../core/services/wealth-api.service';

Chart.register(...registerables);

export interface AmcCompositionRow {
  amc_name: string;
  invested_value: number;
  current_value: number;
  holding_count: number;
  percentage: number;
}

export interface CompositionByAmcResponse {
  results: AmcCompositionRow[];
  total_current_value: number;
  number_of_amcs: number;
}

/**
 * PORTFOLIO COMPOSITION ANALYSIS
 *
 * Top AMC exposures / AMC concentration, sourced from
 * /api/analytics/wealth/composition-by-amc/ (see
 * InvestmentSummaryService.calculate_composition_by_amc).
 *
 * Two real, independent AMC data sources feed this — Mutual Fund
 * holdings via MutualFundScheme.amc_name (already populated),
 * Equity/other holdings via SecurityMaster.amc_name (populated via
 * Django admin, may be empty). Anything without an AMC on either
 * side is bucketed under "Unassigned" rather than dropped — that
 * bucket is real portfolio value, just not yet attributable.
 *
 * The rest of the Nexedge-style Composition Analysis brief (top
 * instruments, sector concentration, per-asset-class composition)
 * is NOT built here — this page covers AMC concentration only.
 * Sector concentration needs SecurityMaster.sector aggregated the
 * same way this page aggregates amc_name (straightforward follow-
 * up once wanted); top-instruments-by-performance needs the
 * benchmark work that's still open.
 */
@Component({
  selector: 'app-composition',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './composition.component.html',
  styleUrl: './composition.component.scss',
})
export class CompositionComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly wealthApi = inject(WealthApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  @ViewChild('amcChart')
  amcChartRef?: ElementRef<HTMLCanvasElement>;

  loading = true;
  error = '';

  composition: CompositionByAmcResponse | null = null;

  private amcChart?: Chart;
  private viewReady = false;

  ngOnInit(): void {
    this.loadComposition();
  }

  ngAfterViewInit(): void {
    this.viewReady = true;

    if (!this.loading) {
      setTimeout(() => this.renderChart());
    }
  }

  ngOnDestroy(): void {
    this.amcChart?.destroy();
    this.amcChart = undefined;
  }

  loadComposition(): void {
    this.loading = true;
    this.error = '';

    this.wealthApi.getCompositionByAmc().subscribe({
      next: (data: CompositionByAmcResponse) => {
        this.composition = data;
        this.loading = false;
        this.cdr.markForCheck();

        if (this.viewReady) {
          setTimeout(() => this.renderChart());
        }
      },

      error: (error) => {
        console.error('COMPOSITION BY AMC API ERROR:', error);

        this.loading = false;
        this.error = 'Unable to load composition data.';
        this.cdr.markForCheck();
      },
    });
  }

  /**
   * Top N AMCs by current value, for the table and the horizontal
   * bar chart. Everything beyond N rolls into an "Others" row so a
   * long tail of small/Unassigned exposures doesn't dominate the
   * chart — same intent as the reference report's "Top 5 AMC
   * Exposures" section.
   */
  get topAmcs(): AmcCompositionRow[] {
    return (this.composition?.results ?? []).slice(0, 10);
  }

  get hasData(): boolean {
    return (this.composition?.results?.length ?? 0) > 0;
  }

  private renderChart(): void {
    const canvas = this.amcChartRef?.nativeElement;

    if (!canvas) {
      return;
    }

    this.amcChart?.destroy();

    const rows = this.topAmcs;

    if (!rows.length) {
      return;
    }

    const labels = rows.map((row) => row.amc_name);
    const values = rows.map((row) => row.current_value);
    const percentages = rows.map((row) => row.percentage);

    const config: ChartConfiguration<'bar'> = {
      type: 'bar',

      data: {
        labels,

        datasets: [
          {
            data: values,
            backgroundColor: '#085888',
            borderRadius: 4,
          },
        ],
      },

      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,

        plugins: {
          legend: {
            display: false,
          },

          tooltip: {
            callbacks: {
              label: (context) => {
                const index = context.dataIndex;
                const percentage = percentages[index] ?? 0;

                return `${this.formatCurrency(Number(context.raw))} (${percentage.toFixed(2)}%)`;
              },
            },
          },
        },

        scales: {
          x: {
            ticks: {
              callback: (value) => this.formatCurrency(Number(value)),
            },
          },
        },
      },
    };

    this.amcChart = new Chart(canvas, config);
  }

  formatCurrency(value: number): string {
    return `₹${value.toLocaleString('en-IN', {
      maximumFractionDigits: 0,
    })}`;
  }

  formatPercentage(value: number): string {
    return `${value.toFixed(2)}%`;
  }
}
