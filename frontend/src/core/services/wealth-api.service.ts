import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';

import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class WealthApiService {
  private readonly http = inject(HttpClient);

  /*
   * IMPORTANT:
   *
   * Frontend:
   *     http://localhost:4200
   *
   * Backend:
   *     http://localhost:8000
   *
   * Use localhost for both so the Django session cookie
   * belongs to the same site.
   */
  private readonly baseUrl = 'http://localhost:8000/api/analytics/wealth';

  getSummary(family?: string): Observable<any> {
    let params = new HttpParams();

    if (family) {
      params = params.set('family', family);
    }

    return this.http.get<any>(`${this.baseUrl}/summary/`, {
      params,
      withCredentials: true,
    });
  }

  getAllocation(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/allocation/`, {
      withCredentials: true,
    });
  }

  getPerformance(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/performance/`, {
      withCredentials: true,
    });
  }

  getXirr(family?: string): Observable<any> {
    let params = new HttpParams();

    if (family) {
      params = params.set('family', family);
    }

    return this.http.get<any>(`${this.baseUrl}/xirr/`, {
      params,
      withCredentials: true,
    });
  }

  getInvestmentSummary(family?: string): Observable<any> {
    let params = new HttpParams();

    if (family) {
      params = params.set('family', family);
    }

    return this.http.get<any>(`${this.baseUrl}/investment-summary/`, {
      params,
      withCredentials: true,
    });
  }

  getPerformanceBySubclass(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/performance-by-subclass/`, {
      withCredentials: true,
    });
  }

  getAllocationByAdvisor(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/allocation-by-advisor/`, {
      withCredentials: true,
    });
  }

  getPerformanceByAdvisor(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/performance-by-advisor/`, {
      withCredentials: true,
    });
  }

  getHistorical(days: number = 30, family?: string): Observable<any> {
    let params = new HttpParams().set('days', days);

    if (family) {
      params = params.set('family', family);
    }

    return this.http.get<any>(`${this.baseUrl}/historical/`, {
      params,
      withCredentials: true,
    });
  }
}
