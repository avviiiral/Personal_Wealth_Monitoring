import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { PortfolioComponent } from './portfolio.component';
import {
  PortfolioApiService,
  PortfolioTreeResponse,
} from '../../core/services/portfolio-api.service';

describe('PortfolioComponent', () => {
  let component: PortfolioComponent;
  let fixture: ComponentFixture<PortfolioComponent>;
  let portfolioApi: {
    getPortfolioTree: ReturnType<typeof vi.fn>;
  };

  const mockResponse: PortfolioTreeResponse = {
    success: true,
    count: 1,
    families: [
      {
        family_name: 'Family A',
        portfolio_count: 1,
        portfolios: [
          {
            portfolio: 'Portfolio A',
            asset_class_count: 1,
            asset_classes: [
              {
                asset_class: 'Equity',
                sub_class_count: 1,
                sub_classes: [
                  {
                    sub_class: 'Large Cap',
                    asset_count: 1,
                    assets: [
                      {
                        id: 1,
                        asset_name: 'Test Equity',
                        underlying: '',
                        isin: 'INE000TEST001',
                        advisors: '',
                        quantity: 10,
                        average_cost: 100,
                        invested_value: 1000,
                        current_price: 120,
                        current_value: 1200,
                        pnl: 200,
                        pnl_percentage: 20,
                        xirr: 20,
                        sector: 'Technology',
                        cap_type: 'Large Cap',
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  };

  beforeEach(async () => {
    portfolioApi = {
      getPortfolioTree: vi.fn().mockReturnValue(of(mockResponse)),
    };

    await TestBed.configureTestingModule({
      imports: [PortfolioComponent],
      providers: [
        {
          provide: PortfolioApiService,
          useValue: portfolioApi,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PortfolioComponent);

    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load portfolio hierarchy', () => {
    expect(component.families.length).toBe(1);

    expect(component.families[0].family_name).toBe('Family A');

    expect(component.families[0].portfolios[0].portfolio).toBe('Portfolio A');
  });

  it('should expose asset classes', () => {
    expect(component.availableAssetClasses.length).toBe(1);

    expect(component.availableAssetClasses[0].asset_class).toBe('Equity');
  });

  it('should expose sub classes', () => {
    expect(component.availableSubClasses.length).toBe(1);

    expect(component.availableSubClasses[0].sub_class).toBe('Large Cap');
  });

  it('should expose portfolio groups', () => {
    expect(component.portfolioGroups.length).toBe(1);

    expect(component.portfolioGroups[0].family_name).toBe('Family A');

    expect(component.portfolioGroups[0].portfolio).toBe('Portfolio A');
  });

  it('should calculate asset count', () => {
    const group = component.portfolioGroups[0];

    expect(component.getGroupAssetCount(group)).toBe(1);
  });

  it('should filter by family', () => {
    component.selectFamily('Family A');

    expect(component.selectedFamily).toBe('Family A');

    expect(component.filteredFamilies.length).toBe(1);
  });

  it('should filter by asset class', () => {
    component.selectAssetClass('Equity');

    expect(component.selectedAssetClass).toBe('Equity');

    expect(component.filteredAssetClasses.length).toBe(1);
  });

  it('should filter by sub class', () => {
    component.selectSubClass('Large Cap');

    expect(component.selectedSubClass).toBe('Large Cap');

    expect(component.availableSubClasses.length).toBe(1);
  });

  it('should clear filters', () => {
    component.selectFamily('Family A');
    component.selectPortfolio('Portfolio A');
    component.selectAssetClass('Equity');
    component.selectSubClass('Large Cap');

    component.clearFamily();

    expect(component.selectedFamily).toBe('');
    expect(component.selectedPortfolio).toBe('');
    expect(component.selectedAssetClass).toBe('');
    expect(component.selectedSubClass).toBe('');
  });

  it('should handle API errors', () => {
    portfolioApi.getPortfolioTree.mockReturnValue(
      throwError(() => ({
        status: 500,
      })),
    );

    component.loadPortfolio();

    expect(component.error).toBe('Unable to load portfolio data.');
  });
});
