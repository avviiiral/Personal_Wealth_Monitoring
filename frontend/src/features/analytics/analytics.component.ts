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

import { forkJoin } from 'rxjs';

import { WealthApiService } from '../../core/services/wealth-api.service';

Chart.register(...registerables);

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './analytics.component.html',
  styleUrl: './analytics.component.scss',
})
export class AnalyticsComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly wealthApi = inject(WealthApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  @ViewChild('historicalChart')
  historicalChartRef?: ElementRef<HTMLCanvasElement>;

  @ViewChild('allocationChart')
  allocationChartRef?: ElementRef<HTMLCanvasElement>;

  @ViewChild('performanceChart')
  performanceChartRef?: ElementRef<HTMLCanvasElement>;

  loading = true;
  error = '';

  summary: any = null;
  allocation: any = null;
  performance: any = null;
  xirr: any = null;
  historical: any = null;

  selectedDays = 30;

  bestPerformer: any = null;
  worstPerformer: any = null;
  largestAllocation: any = null;

  periodValueChange = 0;

  private historicalChart?: Chart;
  private allocationChart?: Chart;
  private performanceChart?: Chart;

  ngOnInit(): void {
    this.loadAnalytics();
  }

  ngAfterViewInit(): void {
    // Charts are rendered after API data is loaded
    // and Angular has created the canvas elements.
  }

  loadAnalytics(): void {
    this.loading = true;
    this.error = '';

    this.destroyCharts();

    forkJoin({
      summary: this.wealthApi.getSummary(),
      allocation: this.wealthApi.getAllocation(),
      performance: this.wealthApi.getPerformance(),
      historical: this.wealthApi.getHistorical(this.selectedDays),
    }).subscribe({
      next: (data) => {
        console.log('Analytics API response:', data);

        try {
          this.summary = data.summary;
          this.allocation = data.allocation;
          this.performance = data.performance;
          this.xirr = {
            xirr_percentage: this.summary?.xirr_percentage ?? null,
          };
          this.historical = data.historical;

          console.log('Analytics summary:', this.summary);
          console.log('Analytics allocation:', this.allocation);
          console.log('Analytics performance:', this.performance);
          console.log('Analytics xirr:', this.xirr);
          console.log('Analytics historical:', this.historical);

          this.calculateInsights();

          console.log('Analytics insights calculated successfully');
        } catch (processingError) {
          console.error('Analytics response processing error:', processingError);

          this.error = 'Analytics data was received, but could not be processed.';
        } finally {
          /*
           * Important:
           * loading must become false before trying to access
           * the canvas elements controlled by *ngIf.
           */
          this.loading = false;

          /*
           * Immediately tell Angular that the loading state changed.
           * This allows the chart section to be created in the DOM.
           */
          this.cdr.detectChanges();

          /*
           * Wait one tick so @ViewChild canvas references exist.
           */
          setTimeout(() => {
            this.renderCharts();
          }, 0);
        }
      },

      error: (error) => {
        console.error('Analytics API loading error:', error);

        this.loading = false;

        this.error = 'Unable to load analytics data. Please refresh and try again.';

        this.cdr.detectChanges();
      },
    });
  }

  changePeriod(days: number): void {
    if (this.selectedDays === days) {
      return;
    }

    this.selectedDays = days;

    this.loadAnalytics();
  }

  private calculateInsights(): void {
    const performanceResults = this.performance?.results ?? [];

    if (performanceResults.length) {
      const sorted = [...performanceResults].sort(
        (a: any, b: any) => this.toNumber(b.pnl_percentage) - this.toNumber(a.pnl_percentage),
      );

      this.bestPerformer = sorted[0];
      this.worstPerformer = sorted[sorted.length - 1];
    } else {
      this.bestPerformer = null;
      this.worstPerformer = null;
    }

    const allocationResults = this.allocation?.results ?? [];

    if (allocationResults.length) {
      this.largestAllocation = [...allocationResults].sort(
        (a: any, b: any) => this.toNumber(b.percentage) - this.toNumber(a.percentage),
      )[0];
    } else {
      this.largestAllocation = null;
    }

    const historicalResults = this.historical?.results ?? [];

    if (historicalResults.length >= 2) {
      const first = this.toNumber(historicalResults[0].portfolio_value);

      const last = this.toNumber(historicalResults[historicalResults.length - 1].portfolio_value);

      if (first > 0) {
        this.periodValueChange = ((last - first) / first) * 100;
      } else {
        this.periodValueChange = 0;
      }
    } else {
      this.periodValueChange = 0;
    }
  }

  private renderCharts(): void {
    if (this.loading) {
      return;
    }

    this.renderHistoricalChart();
    this.renderAllocationChart();
    this.renderPerformanceChart();
  }

  private renderHistoricalChart(): void {
    const canvas = this.historicalChartRef?.nativeElement;

    if (!canvas) {
      console.warn('Historical chart canvas not available.');
      return;
    }

    this.historicalChart?.destroy();

    const results = this.historical?.results ?? [];

    if (!results.length) {
      console.warn('No historical data available for wealth chart.');
      return;
    }

    const labels = results.map((item: any) => this.formatDate(item.date));

    const portfolioValues = results.map((item: any) => this.toNumber(item.portfolio_value));

    const investedValues = results.map((item: any) => this.toNumber(item.invested_value));

    const config: ChartConfiguration<'line'> = {
      type: 'line',

      data: {
        labels,

        datasets: [
          {
            label: 'Portfolio Value',
            data: portfolioValues,

            borderColor: '#111827',
            backgroundColor: 'rgba(17, 24, 39, 0.07)',

            borderWidth: 2,
            fill: true,
            tension: 0.35,

            pointRadius: 0,
            pointHoverRadius: 5,
          },

          {
            label: 'Invested Capital',
            data: investedValues,

            borderColor: '#9ca3af',
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
              maxTicksLimit: 10,
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

    this.historicalChart = new Chart(canvas, config);
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
              '#374151',
              '#6b7280',
              '#9ca3af',
              '#d1d5db',
              '#4b5563',
              '#1f2937',
              '#e5e7eb',
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
              padding: 14,
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

  private renderPerformanceChart(): void {
    const canvas = this.performanceChartRef?.nativeElement;

    if (!canvas) {
      console.warn('Performance chart canvas not available.');
      return;
    }

    this.performanceChart?.destroy();

    const results = this.performance?.results ?? [];

    if (!results.length) {
      console.warn('No performance data available.');
      return;
    }

    const sortedResults = [...results].sort(
      (a: any, b: any) => this.toNumber(b.pnl_percentage) - this.toNumber(a.pnl_percentage),
    );

    const labels = sortedResults.map(
      (item: any) => item.symbol || item.asset_name || item.scheme_name || item.name || 'Unknown',
    );

    const values = sortedResults.map((item: any) => this.toNumber(item.pnl_percentage));

    const backgroundColors = values.map((value) => (value >= 0 ? '#111827' : '#9ca3af'));

    const config: ChartConfiguration<'bar'> = {
      type: 'bar',

      data: {
        labels,

        datasets: [
          {
            label: 'Return %',
            data: values,

            backgroundColor: backgroundColors,

            borderRadius: 5,
            barThickness: 24,
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
              label: (context) => `Return: ${this.toNumber(context.parsed.x).toFixed(2)}%`,
            },
          },
        },

        scales: {
          x: {
            ticks: {
              callback: (value) => `${Number(value).toFixed(0)}%`,
            },

            grid: {
              color: '#eef0f3',
            },
          },

          y: {
            grid: {
              display: false,
            },
          },
        },
      },
    };

    this.performanceChart = new Chart(canvas, config);
  }

  private destroyCharts(): void {
    this.historicalChart?.destroy();
    this.allocationChart?.destroy();
    this.performanceChart?.destroy();

    this.historicalChart = undefined;
    this.allocationChart = undefined;
    this.performanceChart = undefined;
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

  formatAxisCurrency(value: number): string {
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

  formatDate(value: string): string {
    if (!value) {
      return '';
    }

    const date = new Date(`${value}T00:00:00`);

    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
    });
  }

  formatCategory(value: string): string {
    if (!value) {
      return 'Unknown';
    }

    return value
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  getBestPerformerName(): string {
    if (!this.bestPerformer) {
      return '-';
    }

    return (
      this.bestPerformer.symbol ||
      this.bestPerformer.asset_name ||
      this.bestPerformer.scheme_name ||
      this.bestPerformer.name ||
      'Unknown'
    );
  }

  getWorstPerformerName(): string {
    if (!this.worstPerformer) {
      return '-';
    }

    return (
      this.worstPerformer.symbol ||
      this.worstPerformer.asset_name ||
      this.worstPerformer.scheme_name ||
      this.worstPerformer.name ||
      'Unknown'
    );
  }

  getBestPerformerReturn(): number {
    return this.toNumber(this.bestPerformer?.pnl_percentage);
  }

  getWorstPerformerReturn(): number {
    return this.toNumber(this.worstPerformer?.pnl_percentage);
  }

  getLargestAllocationName(): string {
    if (!this.largestAllocation) {
      return '-';
    }

    return this.formatCategory(this.largestAllocation.category);
  }

  getLargestAllocationPercentage(): number {
    return this.toNumber(this.largestAllocation?.percentage);
  }
}
