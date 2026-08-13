import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import {
  PortfolioApiService,
  CreateAssetRequest,
  CreateTransactionRequest,
} from '../../core/services/portfolio-api.service';

import {
  MutualFundsApiService,
  MutualFundScheme,
  CreateMutualFundSchemeRequest,
  CreateMutualFundTransactionRequest,
  CreateSIPRequest,
} from '../../core/services/mutual-funds-api.service';

@Component({
  selector: 'app-add-investment',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-investment.component.html',
  styleUrl: './add-investment.component.scss',
})
export class AddInvestmentComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);

  private readonly mutualFundsApi = inject(MutualFundsApiService);

  private readonly router = inject(Router);

  private readonly cdr = inject(ChangeDetectorRef);

  saving = false;

  error = '';

  success = '';

  investmentType = 'STOCK';

  // ==========================================================
  // STOCK / ETF / OTHER ASSET
  // ==========================================================

  asset = {
    name: '',
    category: 'STOCK',
    symbol: '',
    isin: '',
    institution: '',
    currency: 'INR',
  };

  transaction = {
    transaction_type: 'BUY',
    transaction_date: '',
    quantity: 0,
    price_per_unit: 0,
    amount: 0,
    fees: 0,
    notes: '',
  };

  // ==========================================================
  // MUTUAL FUND
  // ==========================================================

  mutualFund = {
    scheme_name: '',
    amc_name: '',
    scheme_code: '',
    isin_growth: '',
    isin_dividend: '',
    plan: 'Direct',
    option: 'Growth',
    category: '',
  };

  mutualFundTransaction = {
    transaction_type: 'PURCHASE',
    transaction_date: '',
    units: 0,
    nav: 0,
    amount: 0,
    fees: 0,
    notes: '',
  };

  // ==========================================================
  // SIP
  // ==========================================================

  sip = {
    scheme: null as number | null,
    amount: 0,
    frequency: 'MONTHLY',
    start_date: '',
    end_date: '',
    next_installment_date: '',
    is_active: true,
  };

  // ==========================================================
  // MUTUAL FUND SCHEMES
  // ==========================================================

  schemes: MutualFundScheme[] = [];

  schemeSearch = '';

  schemeSearchLoading = false;

  selectedScheme: MutualFundScheme | null = null;

  // ==========================================================
  // OPTIONS
  // ==========================================================

  readonly investmentTypes = [
    { value: 'STOCK', label: 'Stock' },
    { value: 'ETF', label: 'ETF' },
    { value: 'MUTUAL_FUND', label: 'Mutual Fund' },
    { value: 'SIP', label: 'SIP' },
  ];

  readonly transactionTypes = [
    { value: 'BUY', label: 'Buy' },
    { value: 'SELL', label: 'Sell' },
    { value: 'DIVIDEND', label: 'Dividend' },
    { value: 'INTEREST', label: 'Interest' },
    { value: 'DEPOSIT', label: 'Deposit' },
    { value: 'WITHDRAWAL', label: 'Withdrawal' },
    { value: 'BONUS', label: 'Bonus' },
    { value: 'SPLIT', label: 'Split' },
    { value: 'OTHER', label: 'Other' },
  ];

  readonly mutualFundTransactionTypes = [
    { value: 'PURCHASE', label: 'Purchase' },
    { value: 'SIP', label: 'SIP' },
    { value: 'REDEMPTION', label: 'Redemption' },
    { value: 'DIVIDEND', label: 'Dividend' },
  ];

  readonly sipFrequencies = [
    { value: 'MONTHLY', label: 'Monthly' },
    { value: 'WEEKLY', label: 'Weekly' },
    { value: 'QUARTERLY', label: 'Quarterly' },
    { value: 'YEARLY', label: 'Yearly' },
  ];

  ngOnInit(): void {
    const today = this.getToday();

    this.transaction.transaction_date = today;

    this.mutualFundTransaction.transaction_date = today;

    this.sip.start_date = today;

    this.sip.next_installment_date = today;

    this.calculateAmount();

    this.calculateMutualFundAmount();
  }

  // ==========================================================
  // DATE
  // ==========================================================

  private getToday(): string {
    const today = new Date();

    const year = today.getFullYear();

    const month = String(today.getMonth() + 1).padStart(2, '0');

    const day = String(today.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }

  // ==========================================================
  // LOAD MUTUAL FUND SCHEMES
  // ==========================================================

  loadSchemes(search = ''): void {
    this.schemeSearchLoading = true;

    this.mutualFundsApi.getSchemes(search).subscribe({
      next: (response) => {
        this.schemes = response.results;

        this.schemeSearchLoading = false;

        this.cdr.detectChanges();
      },

      error: (error) => {
        console.error('Unable to load mutual fund schemes:', error);

        this.schemeSearchLoading = false;

        this.schemes = [];

        this.cdr.detectChanges();
      },
    });
  }

  onSchemeSearchChange(): void {
    const search = this.schemeSearch.trim();

    this.selectedScheme = null;

    if (search.length < 2) {
      this.schemes = [];

      return;
    }

    this.loadSchemes(search);
  }

  onSchemeSelected(schemeId: number | null): void {
    if (!schemeId) {
      this.selectedScheme = null;

      return;
    }

    const scheme = this.schemes.find((item) => item.id === Number(schemeId));

    if (!scheme) {
      return;
    }

    this.selectedScheme = scheme;

    this.sip.scheme = scheme.id;

    this.mutualFund.scheme_name = scheme.scheme_name;

    this.mutualFund.amc_name = scheme.amc_name || '';

    this.mutualFund.scheme_code = scheme.scheme_code || '';

    this.mutualFund.isin_growth = scheme.isin_growth || '';

    this.mutualFund.isin_dividend = scheme.isin_dividend || '';

    this.mutualFund.plan = scheme.plan || '';

    this.mutualFund.option = scheme.option || '';

    this.mutualFund.category = scheme.category || '';

    this.cdr.detectChanges();
  }

  // ==========================================================
  // CHANGE INVESTMENT TYPE
  // ==========================================================

  onInvestmentTypeChange(): void {
    this.error = '';

    this.success = '';

    this.schemeSearch = '';

    this.schemes = [];

    this.selectedScheme = null;

    this.sip.scheme = null;
  }

  // ==========================================================
  // STOCK / ETF AMOUNT
  // ==========================================================

  calculateAmount(): void {
    const quantity = Number(this.transaction.quantity) || 0;

    const price = Number(this.transaction.price_per_unit) || 0;

    this.transaction.amount = Number((quantity * price).toFixed(2));
  }

  // ==========================================================
  // MUTUAL FUND AMOUNT
  // ==========================================================

  calculateMutualFundAmount(): void {
    const units = Number(this.mutualFundTransaction.units) || 0;

    const nav = Number(this.mutualFundTransaction.nav) || 0;

    this.mutualFundTransaction.amount = Number((units * nav).toFixed(2));
  }

  // ==========================================================
  // ADD INVESTMENT
  // ==========================================================

  addInvestment(): void {
    if (this.saving) {
      return;
    }

    this.error = '';

    this.success = '';

    if (this.investmentType === 'MUTUAL_FUND') {
      this.addMutualFund();

      return;
    }

    if (this.investmentType === 'SIP') {
      this.addSIP();

      return;
    }

    this.addPortfolioInvestment();
  }

  // ==========================================================
  // STOCK / ETF
  // ==========================================================

  private addPortfolioInvestment(): void {
    if (!this.asset.name.trim()) {
      this.error = 'Investment name is required.';

      return;
    }

    if (!this.transaction.transaction_date) {
      this.error = 'Transaction date is required.';

      return;
    }

    this.saving = true;

    const payload: CreateAssetRequest = {
      name: this.asset.name.trim(),

      category: this.investmentType,

      symbol: this.asset.symbol.trim() || null,

      isin: this.asset.isin.trim() || null,

      institution: this.asset.institution.trim() || null,

      currency: this.asset.currency,
    };

    this.portfolioApi.createAsset(payload).subscribe({
      next: (createdAsset) => {
        const transactionPayload: CreateTransactionRequest = {
          asset: createdAsset.id,

          transaction_type: this.transaction.transaction_type,

          transaction_date: this.transaction.transaction_date,

          quantity: Number(this.transaction.quantity),

          price_per_unit: Number(this.transaction.price_per_unit),

          amount: Number(this.transaction.amount),

          fees: Number(this.transaction.fees) || 0,

          notes: this.transaction.notes.trim() || null,
        };

        this.portfolioApi.createTransaction(transactionPayload).subscribe({
          next: () => {
            this.finishSuccess('Investment added successfully.');
          },

          error: (error) => {
            this.handleError(
              error,
              'Investment was created, but the transaction could not be created.',
            );
          },
        });
      },

      error: (error) => {
        this.handleError(error, 'Unable to create investment.');
      },
    });
  }

  // ==========================================================
  // MUTUAL FUND
  // ==========================================================

  private addMutualFund(): void {
    if (!this.mutualFund.scheme_name.trim()) {
      this.error = 'Mutual fund scheme name is required.';

      return;
    }

    if (!this.mutualFundTransaction.transaction_date) {
      this.error = 'Transaction date is required.';

      return;
    }

    this.saving = true;

    const schemePayload: CreateMutualFundSchemeRequest = {
      scheme_name: this.mutualFund.scheme_name.trim(),

      amc_name: this.mutualFund.amc_name.trim() || null,

      scheme_code: this.mutualFund.scheme_code.trim() || null,

      isin_growth: this.mutualFund.isin_growth.trim() || null,

      isin_dividend: this.mutualFund.isin_dividend.trim() || null,

      plan: this.mutualFund.plan.trim() || null,

      option: this.mutualFund.option.trim() || null,

      category: this.mutualFund.category.trim() || null,
    };

    this.mutualFundsApi.createScheme(schemePayload).subscribe({
      next: (scheme) => {
        const transactionPayload: CreateMutualFundTransactionRequest = {
          scheme: scheme.id,

          transaction_type: this.mutualFundTransaction.transaction_type,

          transaction_date: this.mutualFundTransaction.transaction_date,

          units: Number(this.mutualFundTransaction.units),

          nav: Number(this.mutualFundTransaction.nav),

          amount: Number(this.mutualFundTransaction.amount),

          fees: Number(this.mutualFundTransaction.fees) || 0,

          notes: this.mutualFundTransaction.notes.trim() || null,
        };

        this.mutualFundsApi.createTransaction(transactionPayload).subscribe({
          next: () => {
            this.finishSuccess('Mutual fund investment added successfully.');
          },

          error: (error) => {
            this.handleError(
              error,
              'Mutual fund was created, but the transaction could not be created.',
            );
          },
        });
      },

      error: (error) => {
        this.handleError(error, 'Unable to create mutual fund.');
      },
    });
  }

  // ==========================================================
  // SIP
  // ==========================================================

  private addSIP(): void {
    if (!this.sip.scheme) {
      this.error = 'Please select a mutual fund scheme.';

      return;
    }

    if (Number(this.sip.amount) <= 0) {
      this.error = 'SIP amount must be greater than zero.';

      return;
    }

    if (!this.sip.start_date) {
      this.error = 'SIP start date is required.';

      return;
    }

    this.saving = true;

    const payload: CreateSIPRequest = {
      scheme: Number(this.sip.scheme),

      amount: Number(this.sip.amount),

      frequency: this.sip.frequency,

      start_date: this.sip.start_date,

      end_date: this.sip.end_date || null,

      next_installment_date: this.sip.next_installment_date || this.sip.start_date,

      is_active: this.sip.is_active,
    };

    this.mutualFundsApi.createSIP(payload).subscribe({
      next: () => {
        this.finishSuccess('SIP added successfully.');
      },

      error: (error) => {
        this.handleError(error, 'Unable to create SIP.');
      },
    });
  }

  // ==========================================================
  // SUCCESS
  // ==========================================================

  private finishSuccess(message: string): void {
    this.saving = false;

    this.success = message;

    this.cdr.detectChanges();

    setTimeout(() => {
      this.router.navigate(['/portfolio']);
    }, 800);
  }

  // ==========================================================
  // ERROR
  // ==========================================================

  private handleError(error: any, fallback: string): void {
    console.error('Add investment error:', error);

    this.saving = false;

    this.error =
      error?.error?.detail ||
      error?.error?.error ||
      error?.error?.non_field_errors?.[0] ||
      fallback;

    this.cdr.detectChanges();
  }

  cancel(): void {
    this.router.navigate(['/portfolio']);
  }
}
