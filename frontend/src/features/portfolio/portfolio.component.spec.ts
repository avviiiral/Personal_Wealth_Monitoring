import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { PortfolioComponent } from './portfolio.component';

import {
  PortfolioApiService,
  PortfolioTreeResponse,
} from '../../core/services/portfolio-api.service';

import { ManualPriceService } from '../../core/services/manual-price.service';

describe('PortfolioComponent', () => {
  let component: PortfolioComponent;
  let fixture: ComponentFixture<PortfolioComponent>;

  let portfolioApi: {
    getPortfolioTree: ReturnType<typeof vi.fn>;
  };

  let manualPriceService: {
    updatePrice: ReturnType<typeof vi.fn>;
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

    manualPriceService = {
      updatePrice: vi.fn().mockReturnValue(
        of({
          success: true,
          message: 'Price updated successfully.',
        }),
      ),
    };

    await TestBed.configureTestingModule({
      imports: [PortfolioComponent],

      providers: [
        {
          provide: PortfolioApiService,
          useValue: portfolioApi,
        },

        {
          provide: ManualPriceService,
          useValue: manualPriceService,
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

  // ==========================================================
  // BASIC CREATION
  // ==========================================================

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ==========================================================
  // PORTFOLIO LOADING
  // ==========================================================

  it('should load portfolio hierarchy', () => {
    expect(component.families.length).toBe(1);

    expect(component.families[0].family_name).toBe('Family A');

    expect(component.families[0].portfolios[0].portfolio).toBe('Portfolio A');
  });

  // ==========================================================
  // FAMILY OPTIONS
  // ==========================================================

  it('should expose family options', () => {
    expect(component.familyOptions.length).toBe(1);

    expect(component.familyOptions[0]).toBe('Family A');
  });

  // ==========================================================
  // ASSET CLASS OPTIONS
  // ==========================================================

  it('should expose asset class options', () => {
    expect(component.assetClassOptions.length).toBe(1);

    expect(component.assetClassOptions[0]).toBe('Equity');
  });

  // ==========================================================
  // FILTERED FAMILIES
  // ==========================================================

  it('should return all families when no family is selected', () => {
    expect(component.filteredFamilies.length).toBe(1);
  });

  it('should filter by family', () => {
    component.selectFamily('Family A');

    expect(component.selectedFamily).toBe('Family A');

    expect(component.filteredFamilies.length).toBe(1);

    expect(component.filteredFamilies[0].family_name).toBe('Family A');
  });

  it('should clear family selection when selecting the same family again', () => {
    component.selectFamily('Family A');

    expect(component.selectedFamily).toBe('Family A');

    component.selectFamily('Family A');

    expect(component.selectedFamily).toBe('');

    expect(component.filteredFamilies.length).toBe(1);
  });

  // ==========================================================
  // ASSET CLASS FILTERING
  // ==========================================================

  it('should filter by asset class', () => {
    component.selectAssetClass('Equity');

    expect(component.selectedAssetClass).toBe('Equity');

    expect(component.assetClassOptions.length).toBe(1);

    expect(component.assetClassOptions[0]).toBe('Equity');
  });

  it('should clear asset class selection when selecting the same class again', () => {
    component.selectAssetClass('Equity');

    expect(component.selectedAssetClass).toBe('Equity');

    component.selectAssetClass('Equity');

    expect(component.selectedAssetClass).toBe('');
  });

  // ==========================================================
  // SUBCLASS SUMMARIES
  // ==========================================================

  it('should expose subclass summaries', () => {
    expect(component.subClassSummaries.length).toBe(1);

    expect(component.subClassSummaries[0].sub_class).toBe('Large Cap');

    expect(component.subClassSummaries[0].current_value).toBe(1200);

    expect(component.subClassSummaries[0].pnl).toBe(200);

    expect(component.subClassSummaries[0].quantity).toBe(10);

    expect(component.subClassSummaries[0].assets.length).toBe(1);
  });

  // ==========================================================
  // SUBCLASS ASSETS
  // ==========================================================

  it('should return assets for a subclass', () => {
    const assets = component.getSubClassAssets('Large Cap');

    expect(assets.length).toBe(1);

    expect(assets[0].asset_name).toBe('Test Equity');
  });

  it('should return empty assets for an unknown subclass', () => {
    const assets = component.getSubClassAssets('Unknown');

    expect(assets.length).toBe(0);
  });

  // ==========================================================
  // SUBCLASS EXPANSION
  // ==========================================================

  it('should toggle subclass expansion', () => {
    expect(component.expandedSubClass).toBe('');

    component.toggleSubClass('Large Cap');

    expect(component.expandedSubClass).toBe('Large Cap');

    component.toggleSubClass('Large Cap');

    expect(component.expandedSubClass).toBe('');
  });

  // ==========================================================
  // CLEAR FILTERS
  // ==========================================================

  it('should clear family and asset class filters', () => {
    component.selectFamily('Family A');

    component.selectAssetClass('Equity');

    component.toggleSubClass('Large Cap');

    expect(component.selectedFamily).toBe('Family A');

    expect(component.selectedAssetClass).toBe('Equity');

    expect(component.expandedSubClass).toBe('Large Cap');

    component.clearFamily();

    expect(component.selectedFamily).toBe('');

    expect(component.selectedAssetClass).toBe('');

    expect(component.expandedSubClass).toBe('');
  });

  it('should clear only asset class filter', () => {
    component.selectFamily('Family A');

    component.selectAssetClass('Equity');

    component.toggleSubClass('Large Cap');

    component.clearAssetClass();

    expect(component.selectedFamily).toBe('Family A');

    expect(component.selectedAssetClass).toBe('');

    expect(component.expandedSubClass).toBe('');
  });

  // ==========================================================
  // SELECTION HELPERS
  // ==========================================================

  it('should correctly identify selected family', () => {
    expect(component.isFamilySelected('Family A')).toBe(false);

    component.selectFamily('Family A');

    expect(component.isFamilySelected('Family A')).toBe(true);
  });

  it('should correctly identify selected asset class', () => {
    expect(component.isAssetClassSelected('Equity')).toBe(false);

    component.selectAssetClass('Equity');

    expect(component.isAssetClassSelected('Equity')).toBe(true);
  });

  // ==========================================================
  // FORMATTING
  // ==========================================================

  it('should format currency', () => {
    expect(component.formatCurrency(1200)).toContain('1,200');
  });

  it('should format number', () => {
    expect(component.formatNumber(1234.567)).toBe('1,234.57');
  });

  it('should format decimal', () => {
    expect(component.formatDecimal(20)).toBe('20.00');
  });

  it('should format percentage', () => {
    expect(component.formatPercentage(20)).toBe('20.00%');
  });

  it('should format null percentage', () => {
    expect(component.formatPercentage(null)).toBe('-');
  });

  it('should return correct pnl class', () => {
    expect(component.getPnlClass(100)).toBe('positive');

    expect(component.getPnlClass(-100)).toBe('negative');

    expect(component.getPnlClass(0)).toBe('neutral');
  });

  // ==========================================================
  // XIRR
  // ==========================================================

  it('should calculate subclass weighted XIRR', () => {
    const summary = component.subClassSummaries[0];

    expect(summary.xirr).toBe(20);
  });

  // ==========================================================
  // PRICE DATE
  // ==========================================================

  it('should handle missing price date', () => {
    const asset = component.subClassSummaries[0].assets[0];

    expect(component.hasPriceDate(asset)).toBe(false);
  });

  // ==========================================================
  // MANUAL PRICE
  // ==========================================================

  it('should start manual price editing', () => {
    const asset = component.subClassSummaries[0].assets[0];

    component.startEditingPrice(asset);

    expect(component.editingAssetId).toBe(1);

    expect(component.manualPriceInput).toBe('120');
  });

  it('should cancel manual price editing', () => {
    const asset = component.subClassSummaries[0].assets[0];

    component.startEditingPrice(asset);

    component.cancelEditingPrice(asset);

    expect(component.editingAssetId).toBeNull();

    expect(component.manualPriceInput).toBe('');
  });

  it('should reject invalid manual price', () => {
    const asset = component.subClassSummaries[0].assets[0];

    component.startEditingPrice(asset);

    component.manualPriceInput = '0';

    component.saveManualPrice(asset);

    expect(component.getManualPriceError(asset)).toBe('Enter a valid price greater than 0.');

    expect(manualPriceService.updatePrice).not.toHaveBeenCalled();
  });

  // ==========================================================
  // API ERRORS
  // ==========================================================

  it('should handle API errors', () => {
    portfolioApi.getPortfolioTree.mockReturnValue(
      throwError(() => ({
        status: 500,
      })),
    );

    component.loadPortfolio();

    expect(component.error).toBe('Unable to load portfolio data.');
  });

  it('should handle authentication errors', () => {
    portfolioApi.getPortfolioTree.mockReturnValue(
      throwError(() => ({
        status: 401,
      })),
    );

    component.loadPortfolio();

    expect(component.error).toBe('Authentication failed. Please log in again.');
  });
});
