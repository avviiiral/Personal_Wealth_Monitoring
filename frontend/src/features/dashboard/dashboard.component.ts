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

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly wealthApi = inject(WealthApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  @ViewChild('wealthChart')
  wealthChartRef?: ElementRef<HTMLCanvasElement>;

  @ViewChild('allocationChart')
  allocationChartRef?: ElementRef<HTMLCanvasElement>;

  loading = true;
  error = '';

  summary: any = null;
  allocation: any = null;
  xirr: any = null;
  historical: any = null;
  investmentSummary: any = null;
  investmentSummaryError = '';

  private wealthChart?: Chart;
  private allocationChart?: Chart;

  private viewReady = false;

  ngOnInit(): void {
    this.loadDashboard();
  }

  ngAfterViewInit(): void {
    if (!this.loading) {
      setTimeout(() => {
        this.renderCharts();
      });
    }
  }

  loadDashboard(): void {
    console.log('Loading dashboard data...');

    this.loading = true;
    this.error = '';

    this.destroyCharts();

    // SUMMARY
    this.wealthApi.getSummary().subscribe({
      next: (data) => {
        console.log('SUMMARY RESPONSE:', data);

        this.summary = data;

        this.loading = false;

        this.cdr.markForCheck();

        setTimeout(() => {
          this.renderCharts();
          this.cdr.markForCheck();
        });
      },

      error: (error) => {
        console.error('SUMMARY API ERROR:', error);

        this.loading = false;
        this.error = 'Unable to load wealth summary.';

        this.cdr.markForCheck();
      },
    });

    // ALLOCATION
    this.wealthApi.getAllocation().subscribe({
      next: (data) => {
        console.log('ALLOCATION RESPONSE:', data);

        this.allocation = data;

        this.cdr.markForCheck();

        setTimeout(() => {
          this.renderAllocationChart();
          this.cdr.markForCheck();
        });
      },

      error: (error) => {
        console.error('ALLOCATION API ERROR:', error);
      },
    });

    // XIRR
    this.wealthApi.getXirr().subscribe({
      next: (data) => {
        console.log('XIRR RESPONSE:', data);

        this.xirr = data;

        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('XIRR API ERROR:', error);
      },
    });

    // INVESTMENT SUMMARY
    this.investmentSummary = null;
    this.investmentSummaryError = '';

    this.wealthApi.getInvestmentSummary().subscribe({
      next: (data) => {
        console.log('INVESTMENT SUMMARY RESPONSE:', data);

        this.investmentSummary = data;

        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('INVESTMENT SUMMARY API ERROR:', error);

        this.investmentSummaryError = 'Unable to load investment summary.';

        this.cdr.markForCheck();
      },
    });

    // HISTORICAL
    this.wealthApi.getHistorical(30).subscribe({
      next: (data) => {
        console.log('HISTORICAL RESPONSE:', data);

        this.historical = data;

        this.cdr.markForCheck();

        setTimeout(() => {
          this.renderWealthChart();
          this.cdr.markForCheck();
        });
      },

      error: (error) => {
        console.error('HISTORICAL API ERROR:', error);
      },
    });
  }

  private renderCharts(): void {
    if (this.loading) {
      return;
    }

    this.renderWealthChart();
    this.renderAllocationChart();
  }

  private renderWealthChart(): void {
    const canvas = this.wealthChartRef?.nativeElement;

    if (!canvas) {
      console.warn('Wealth chart canvas not available.');
      return;
    }

    this.wealthChart?.destroy();

    const results = this.historical?.results ?? [];

    if (!results.length) {
      console.warn('No historical data available for wealth chart.');
      return;
    }

    const labels = results.map((item: any) => this.formatDate(item.date));

    const investedValues = results.map((item: any) => this.toNumber(item.invested_value));

    const portfolioValues = results.map((item: any) => this.toNumber(item.portfolio_value));

    const config: ChartConfiguration<'line'> = {
      type: 'line',

      data: {
        labels,

        datasets: [
          {
            label: 'Portfolio Value',
            data: portfolioValues,
            borderColor: '#111827',
            backgroundColor: 'rgba(17, 24, 39, 0.08)',
            borderWidth: 2,
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 5,
          },

          {
            label: 'Invested Value',
            data: investedValues,
            borderColor: '#8b95a7',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [6, 5],
            fill: false,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 5,
          },
        ],
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
          mode: 'index',
          intersect: false,
        },

        plugins: {
          legend: {
            position: 'top',
            align: 'end',
          },

          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.parsed.y ?? 0;

                return `${context.dataset.label}: ${this.formatCurrency(value)}`;
              },
            },
          },
        },

        scales: {
          x: {
            grid: {
              display: false,
            },

            ticks: {
              maxTicksLimit: 8,
            },
          },

          y: {
            beginAtZero: false,

            ticks: {
              callback: (value) => this.formatAxisCurrency(Number(value)),
            },
          },
        },
      },
    };

    this.wealthChart = new Chart(canvas, config);
  }

  private renderAllocationChart(): void {
    const canvas = this.allocationChartRef?.nativeElement;

    if (!canvas) {
      console.warn('Allocation chart canvas not available.');
      return;
    }

    this.allocationChart?.destroy();

    const results = this.allocation?.results ?? [];

    if (!results.length) {
      console.warn('No allocation data available.');
      return;
    }

    const labels = results.map((item: any) => this.formatCategory(item.category));

    const values = results.map((item: any) => this.toNumber(item.value));

    const percentages = results.map((item: any) => this.toNumber(item.percentage));

    const config: ChartConfiguration<'doughnut'> = {
      type: 'doughnut',

      data: {
        labels,

        datasets: [
          {
            data: values,

            backgroundColor: [
              '#111827',
              '#334155',
              '#64748b',
              '#94a3b8',
              '#cbd5e1',
              '#475569',
              '#1e293b',
              '#e2e8f0',
            ],

            borderWidth: 2,
            borderColor: '#ffffff',
          },
        ],
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        cutout: '68%',

        plugins: {
          legend: {
            position: 'bottom',

            labels: {
              usePointStyle: true,
              padding: 16,
            },
          },

          tooltip: {
            callbacks: {
              label: (context) => {
                const index = context.dataIndex;
                const percentage = percentages[index] ?? 0;

                return `${context.label}: ${this.formatCurrency(
                  Number(context.raw),
                )} (${percentage.toFixed(2)}%)`;
              },
            },
          },
        },
      },
    };

    this.allocationChart = new Chart(canvas, config);
  }

  private destroyCharts(): void {
    this.wealthChart?.destroy();
    this.allocationChart?.destroy();

    this.wealthChart = undefined;
    this.allocationChart = undefined;
  }

  ngOnDestroy(): void {
    this.destroyCharts();
  }

  private toNumber(value: any): number {
    const number = Number(value);

    return Number.isFinite(number) ? number : 0;
  }

  formatCurrency(value: number): string {
    return `₹${value.toLocaleString('en-IN', {
      maximumFractionDigits: 0,
    })}`;
  }

  formatPercentage(value: number): string {
    return `${this.toNumber(value).toFixed(2)}%`;
  }

  /**
   * Groups the flat Investment Summary rows returned by the API by
   * Asset Category, so the template can render a rowspan-style
   * grouped table without repeating the category on every row.
   */
  get investmentSummaryRows(): Array<{
    asset_category: string;
    asset_class: string;
    current_value: number;
    percentage_of_total: number;
    isFirstInCategory: boolean;
    categoryRowSpan: number;
  }> {
    const results = this.investmentSummary?.results ?? [];

    const rows: Array<{
      asset_category: string;
      asset_class: string;
      current_value: number;
      percentage_of_total: number;
      isFirstInCategory: boolean;
      categoryRowSpan: number;
    }> = [];

    let index = 0;

    while (index < results.length) {
      const category = results[index].asset_category;

      let end = index;

      while (end < results.length && results[end].asset_category === category) {
        end++;
      }

      const categoryRowSpan = end - index;

      for (let i = index; i < end; i++) {
        rows.push({
          asset_category: results[i].asset_category,
          asset_class: results[i].asset_class,
          current_value: this.toNumber(results[i].current_value),
          percentage_of_total: this.toNumber(results[i].percentage_of_total),
          isFirstInCategory: i === index,
          categoryRowSpan,
        });
      }

      index = end;
    }

    return rows;
  }

  private formatAxisCurrency(value: number): string {
    const absolute = Math.abs(value);

    if (absolute >= 10000000) {
      return `₹${(value / 10000000).toFixed(1)}Cr`;
    }

    if (absolute >= 100000) {
      return `₹${(value / 100000).toFixed(1)}L`;
    }

    if (absolute >= 1000) {
      return `₹${(value / 1000).toFixed(0)}K`;
    }

    return `₹${value}`;
  }

  private formatDate(value: string): string {
    if (!value) {
      return '';
    }

    const date = new Date(`${value}T00:00:00`);

    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
    });
  }

  private formatCategory(value: string): string {
    if (!value) {
      return 'Unknown';
    }

    return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  }
}
