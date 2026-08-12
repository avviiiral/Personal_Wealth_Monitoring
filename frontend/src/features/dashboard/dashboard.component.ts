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

  @ViewChild('performanceChart')
  performanceChartRef?: ElementRef<HTMLCanvasElement>;

  @ViewChild('pnlChart')
  pnlChartRef?: ElementRef<HTMLCanvasElement>;

  loading = true;
  error = '';

  summary: any = null;
  allocation: any = null;
  performance: any = null;
  xirr: any = null;
  historical: any = null;

  private wealthChart?: Chart;
  private allocationChart?: Chart;
  private performanceChart?: Chart;
  private pnlChart?: Chart;

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

        // Angular 21 zoneless change detection:
        // explicitly notify Angular that the view has changed.
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

    // PERFORMANCE
    this.wealthApi.getPerformance().subscribe({
      next: (data) => {
        console.log('PERFORMANCE RESPONSE:', data);

        this.performance = data;

        this.cdr.markForCheck();

        setTimeout(() => {
          this.renderPerformanceChart();
          this.cdr.markForCheck();
        });
      },

      error: (error) => {
        console.error('PERFORMANCE API ERROR:', error);
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

    // HISTORICAL
    this.wealthApi.getHistorical(30).subscribe({
      next: (data) => {
        console.log('HISTORICAL RESPONSE:', data);

        this.historical = data;

        this.cdr.markForCheck();

        setTimeout(() => {
          this.renderWealthChart();
          this.renderPnlChart();
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
    this.renderPerformanceChart();
    this.renderPnlChart();
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
      (item: any) => item.symbol || item.asset_name || item.name || 'Unknown',
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
            barThickness: 22,
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

  private renderPnlChart(): void {
    const canvas = this.pnlChartRef?.nativeElement;

    if (!canvas) {
      console.warn('P&L chart canvas not available.');
      return;
    }

    this.pnlChart?.destroy();

    const results = this.historical?.results ?? [];

    if (!results.length) {
      console.warn('No historical data available for P&L chart.');
      return;
    }

    const labels = results.map((item: any) => this.formatDate(item.date));

    const values = results.map((item: any) => this.toNumber(item.pnl));

    const config: ChartConfiguration<'line'> = {
      type: 'line',

      data: {
        labels,

        datasets: [
          {
            label: 'P&L',
            data: values,

            borderColor: '#334155',
            backgroundColor: 'rgba(51, 65, 85, 0.08)',

            borderWidth: 2,
            fill: true,
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
            display: false,
          },

          tooltip: {
            callbacks: {
              label: (context) => `P&L: ${this.formatCurrency(context.parsed.y ?? 0)}`,
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
            ticks: {
              callback: (value) => this.formatAxisCurrency(Number(value)),
            },
          },
        },
      },
    };

    this.pnlChart = new Chart(canvas, config);
  }

  private destroyCharts(): void {
    this.wealthChart?.destroy();
    this.allocationChart?.destroy();
    this.performanceChart?.destroy();
    this.pnlChart?.destroy();

    this.wealthChart = undefined;
    this.allocationChart = undefined;
    this.performanceChart = undefined;
    this.pnlChart = undefined;
  }

  ngOnDestroy(): void {
    this.destroyCharts();
  }

  private toNumber(value: any): number {
    const number = Number(value);

    return Number.isFinite(number) ? number : 0;
  }

  private formatCurrency(value: number): string {
    return `₹${value.toLocaleString('en-IN', {
      maximumFractionDigits: 0,
    })}`;
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
