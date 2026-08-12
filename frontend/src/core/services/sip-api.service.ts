import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SIPSummary {
  total_sips: number;
  active_sips: number;
  total_monthly_commitment: number;

  installments: {
    scheduled: number;
    executed: number;
    due: number;
    skipped: number;
    failed: number;
  };

  actual_sip_invested: number;
  pending_sip_amount: number;

  next_installment: {
    id: number;
    date: string;
    amount: number;
    sip_id: number;
  } | null;
}

export interface SIP {
  id: number;
  scheme: number;
  scheme_name: string;
  amount: number;
  frequency: string;
  frequency_display: string;
  start_date: string;
  end_date: string | null;
  next_installment_date: string | null;
  is_active: boolean;
  status: string;
  due_count: number;
  monthly_commitment: number;
  created_at: string;
  updated_at: string;
}

export interface DueSIP {
  id: number;
  scheme: string;
  amount: number;
  frequency: string;
  next_installment_date: string | null;
  due_count: number;
  status: string;
}

export interface SIPInstallment {
  id: number;
  sip_id: number;
  scheme_name: string;
  frequency: string;
  frequency_display: string;
  scheduled_date: string;
  amount: number;
  status: string;
  status_display: string;
  transaction_id: number | null;
  executed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiListResponse<T> {
  count: number;
  results: T[];
}

@Injectable({
  providedIn: 'root',
})
export class SipApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/mutual-funds';

  private readonly requestOptions = {
    withCredentials: true,
  };

  getSummary(): Observable<SIPSummary> {
    return this.http.get<SIPSummary>(`${this.baseUrl}/sips/summary/`, this.requestOptions);
  }

  getSips(): Observable<ApiListResponse<SIP>> {
    return this.http.get<ApiListResponse<SIP>>(`${this.baseUrl}/sips/`, this.requestOptions);
  }

  getDueSips(): Observable<ApiListResponse<DueSIP>> {
    return this.http.get<ApiListResponse<DueSIP>>(`${this.baseUrl}/sips/due/`, this.requestOptions);
  }

  getInstallments(): Observable<ApiListResponse<SIPInstallment>> {
    return this.http.get<ApiListResponse<SIPInstallment>>(
      `${this.baseUrl}/sip-installments/`,
      this.requestOptions,
    );
  }

  getDueInstallments(): Observable<ApiListResponse<SIPInstallment>> {
    return this.http.get<ApiListResponse<SIPInstallment>>(
      `${this.baseUrl}/sip-installments/?status=DUE`,
      this.requestOptions,
    );
  }

  getInstallmentsForSIP(sipId: number): Observable<ApiListResponse<SIPInstallment>> {
    return this.http.get<ApiListResponse<SIPInstallment>>(
      `${this.baseUrl}/sip-installments/?sip_id=${sipId}`,
      this.requestOptions,
    );
  }

  executeInstallment(installmentId: number): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/sip-installments/${installmentId}/execute/`,
      {},
      this.requestOptions,
    );
  }
}
