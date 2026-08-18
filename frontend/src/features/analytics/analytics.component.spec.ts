import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AnalyticsComponent } from './analytics.component';
import { WealthApiService } from '../../core/services/wealth-api.service';

describe('AnalyticsComponent', () => {
  let component: AnalyticsComponent;
  let fixture: ComponentFixture<AnalyticsComponent>;

  let wealthApi: {
    getSummary: ReturnType<typeof vi.fn>;
    getAllocation: ReturnType<typeof vi.fn>;
    getPerformance: ReturnType<typeof vi.fn>;
    getXirr: ReturnType<typeof vi.fn>;
    getHistorical: ReturnType<typeof vi.fn>;
  };

  const mockSummary = {
    total_invested: 100000,
    total_current_value: 125000,
    total_pnl: 25000,
    unrealized_pnl: 20000,
    realized_pnl: 5000,
    return_percentage: 25,
    xirr_percentage: 18.5,
    number_of_holdings: 3,
  };

  const mockAllocation = {
    results: [
      {
        category: 'STOCK',
        value: 75000,
        percentage: 60,
      },
      {
        category: 'MUTUAL_FUND',
        value: 50000,
        percentage: 40,
      },
    ],
  };

  const mockPerformance = {
    results: [
      {
        type: 'EQUITY',
        symbol: 'TEST',
        asset_name: 'Test Stock',
        pnl_percentage: 30,
      },
      {
        type: 'MUTUAL_FUND',
        scheme_name: 'Test Fund',
        pnl_percentage: 10,
      },
    ],
  };

  const mockXirr = {
    xirr_percentage: 18.5,
  };

  const mockHistorical = {
    days: 30,
    results: [
      {
        date: '2026-01-01',
        invested_value: 90000,
        portfolio_value: 100000,
        pnl: 10000,
      },
      {
        date: '2026-01-30',
        invested_value: 100000,
        portfolio_value: 125000,
        pnl: 25000,
      },
    ],
  };

  beforeEach(async () => {
    wealthApi = {
      getSummary: vi.fn().mockReturnValue(of(mockSummary)),
      getAllocation: vi.fn().mockReturnValue(of(mockAllocation)),
      getPerformance: vi.fn().mockReturnValue(of(mockPerformance)),
      getXirr: vi.fn().mockReturnValue(of(mockXirr)),
      getHistorical: vi.fn().mockReturnValue(of(mockHistorical)),
    };

    await TestBed.configureTestingModule({
      imports: [AnalyticsComponent],
      providers: [
        {
          provide: WealthApiService,
          useValue: wealthApi,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyticsComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load analytics data', () => {
    expect(component.summary).toEqual(mockSummary);
    expect(component.allocation).toEqual(mockAllocation);
    expect(component.performance).toEqual(mockPerformance);
    expect(component.xirr).toEqual(mockXirr);
    expect(component.historical).toEqual(mockHistorical);
  });

  it('should calculate best performer', () => {
    expect(component.getBestPerformerName()).toBe('TEST');
    expect(component.getBestPerformerReturn()).toBe(30);
  });

  it('should calculate worst performer', () => {
    expect(component.getWorstPerformerName()).toBe('Test Fund');
    expect(component.getWorstPerformerReturn()).toBe(10);
  });

  it('should calculate largest allocation', () => {
    expect(component.getLargestAllocationName()).toBe('Stock');
    expect(component.getLargestAllocationPercentage()).toBe(60);
  });

  it('should calculate period value change', () => {
    expect(component.periodValueChange).toBe(25);
  });

  it('should change historical period', () => {
    component.changePeriod(90);

    expect(component.selectedDays).toBe(90);
    expect(wealthApi.getHistorical).toHaveBeenCalledWith(90);
  });

  it('should not reload when selecting the same period', () => {
    wealthApi.getSummary.mockClear();

    component.changePeriod(30);

    expect(wealthApi.getSummary).not.toHaveBeenCalled();
  });

  it('should handle API errors', () => {
    wealthApi.getSummary.mockReturnValue(
      throwError(() => ({
        status: 500,
      })),
    );

    component.loadAnalytics();

    expect(component.loading).toBe(false);
    expect(component.error).toBe('Unable to load analytics data. Please refresh and try again.');
  });

  it('should format currency', () => {
    expect(component.formatCurrency(125000)).toContain('₹');
    expect(component.formatCurrency(125000)).toContain('1,25,000');
  });

  it('should format category names', () => {
    expect(component.formatCategory('MUTUAL_FUND')).toBe('Mutual Fund');
  });

  it('should format dates', () => {
    expect(component.formatDate('2026-01-01')).toBe('01 Jan');
  });
});
