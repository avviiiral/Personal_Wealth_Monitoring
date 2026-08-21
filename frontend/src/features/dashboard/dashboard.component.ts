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
  xirr: any = null;
  historical: any = null;
  investmentSummary: any = null;
  investmentSummaryError = '';

  private wealthChart?: Chart;
  private allocationChart?: Chart;

  private viewReady = false;

  /*
   * Currently expanded Asset Category in the
   * Investment Summary table.
   */
  expandedInvestmentCategory = '';

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

        setTimeout(() => {
          this.renderAllocationChart();
          this.cdr.markForCheck();
        });
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

    const results = this.allocationByCategory;

    if (!results.length) {
      console.warn('No allocation data available.');
      return;
    }

    const labels = results.map((item) => item.category);

    const values = results.map((item) => item.value);

    const percentages = results.map((item) => item.percentage);

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
   * Groups the Investment Summary rows by Asset Category, summing
   * current value and % of total, so the Allocation chart shows the
   * exact same categorization and totals as the Investment Summary
   * table below it — one source of truth for both.
   */
  get allocationByCategory(): Array<{
    category: string;
    value: number;
    percentage: number;
  }> {
    const results = this.investmentSummary?.results ?? [];

    const order: string[] = [];
    const totals = new Map<string, { value: number; percentage: number }>();

    for (const row of results) {
      const category = row.asset_category;

      if (!totals.has(category)) {
        totals.set(category, { value: 0, percentage: 0 });
        order.push(category);
      }

      const entry = totals.get(category)!;

      entry.value += this.toNumber(row.current_value);
      entry.percentage += this.toNumber(row.percentage_of_total);
    }

    return order
      .map((category) => {
        const entry = totals.get(category)!;

        return {
          category,
          value: entry.value,
          percentage: Math.round(entry.percentage * 100) / 100,
        };
      })
      .filter((entry) => entry.value > 0);
  }

  /**
   * Groups the flat Investment Summary API rows by Asset Category.
   *
   * Level 1:
   *   Asset Category
   *
   * Level 2:
   *   Asset Class
   *
   * Clicking an Asset Category expands its Asset Classes directly
   * inside the Dashboard. No Portfolio navigation is performed.
   */
  get investmentSummaryGroups(): Array<{
    asset_category: string;
    current_value: number;
    percentage_of_total: number;
    asset_classes: Array<{
      asset_class: string;
      current_value: number;
      percentage_of_total: number;
    }>;
  }> {
    const results = this.investmentSummary?.results ?? [];

    const groups = new Map<
      string,
      {
        asset_category: string;
        current_value: number;
        percentage_of_total: number;
        asset_classes: Array<{
          asset_class: string;
          current_value: number;
          percentage_of_total: number;
        }>;
      }
    >();

    for (const row of results) {
      const category = row.asset_category || 'Unassigned';
      const assetClass = row.asset_class || 'Unassigned';

      let group = groups.get(category);

      if (!group) {
        group = {
          asset_category: category,
          current_value: 0,
          percentage_of_total: 0,
          asset_classes: [],
        };

        groups.set(category, group);
      }

      const currentValue = this.toNumber(row.current_value);
      const percentage = this.toNumber(row.percentage_of_total);

      group.current_value += currentValue;
      group.percentage_of_total += percentage;

      let classRow = group.asset_classes.find((item) => item.asset_class === assetClass);

      if (!classRow) {
        classRow = {
          asset_class: assetClass,
          current_value: 0,
          percentage_of_total: 0,
        };

        group.asset_classes.push(classRow);
      }

      classRow.current_value += currentValue;
      classRow.percentage_of_total += percentage;
    }

    return Array.from(groups.values()).map((group) => ({
      ...group,

      percentage_of_total: Math.round(group.percentage_of_total * 100) / 100,

      asset_classes: group.asset_classes.map((assetClass) => ({
        ...assetClass,

        percentage_of_total: Math.round(assetClass.percentage_of_total * 100) / 100,
      })),
    }));
  }

  /**
   * Expand / collapse an Asset Category in Investment Summary.
   */
  toggleInvestmentCategory(category: string): void {
    if (this.expandedInvestmentCategory === category) {
      this.expandedInvestmentCategory = '';
      return;
    }

    this.expandedInvestmentCategory = category;
  }

  trackByInvestmentCategory(_index: number, group: { asset_category: string }): string {
    return group.asset_category;
  }

  trackByInvestmentAssetClass(_index: number, row: { asset_class: string }): string {
    return row.asset_class;
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
}
