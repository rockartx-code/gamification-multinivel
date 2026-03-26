import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable, catchError, finalize, forkJoin, of, switchMap } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiKpiCardComponent } from '../../../components/ui-kpi-card/ui-kpi-card.component';
import { AdminCampaign, AssetResponse, CreateAssetPayload } from '../../../models/admin.model';
import { AdminControlService } from '../../../services/admin-control.service';

type CampaignFormField =
  | 'name'
  | 'hook'
  | 'description'
  | 'story'
  | 'feed'
  | 'banner'
  | 'heroImage'
  | 'heroBadge'
  | 'heroTitle'
  | 'heroAccent'
  | 'heroTail'
  | 'heroDescription'
  | 'ctaPrimaryText'
  | 'ctaSecondaryText'
  | 'benefits'
  | 'type';

type CampaignAssetField = 'story' | 'feed' | 'banner' | 'heroImage';

@Component({
  selector: 'app-admin-campaigns',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent, UiKpiCardComponent],
  templateUrl: './admin-campaigns.component.html'
})
export class AdminCampaignsComponent {
  @Input() campaigns: AdminCampaign[] = [];

  readonly PAGE_SIZE = 15;
  campaignSearch = '';
  campaignPage = 0;

  campaignMessage = '';
  isSavingCampaign = false;
  campaignForm = this.getDefaultCampaignForm();
  campaignAssetPreviews = new Map<CampaignAssetField, string>();
  campaignAssetFiles = new Map<CampaignAssetField, File>();
  campaignAssetUploading = new Map<CampaignAssetField, boolean>();

  get filteredCampaigns(): AdminCampaign[] {
    const q = this.campaignSearch.trim().toLowerCase();
    if (!q) return this.campaigns;
    return this.campaigns.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.hook || '').toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q) ||
        (c.type || '').toLowerCase().includes(q) ||
        (c.active ? 'activa' : 'inactiva').includes(q)
    );
  }

  get pagedCampaigns(): AdminCampaign[] {
    return this.filteredCampaigns.slice(this.campaignPage * this.PAGE_SIZE, (this.campaignPage + 1) * this.PAGE_SIZE);
  }

  get campaignsTotalPages(): number {
    return Math.max(1, Math.ceil(this.filteredCampaigns.length / this.PAGE_SIZE));
  }

  pageRange(totalPages: number, current: number): number[] {
    const start = Math.max(0, current - 2);
    const end = Math.min(totalPages - 1, current + 2);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }

  onSearch(value: string): void {
    this.campaignSearch = value;
    this.campaignPage = 0;
  }

  constructor(private readonly adminControl: AdminControlService) {}

  get activeCampaignsCount(): number {
    return this.campaigns.filter((campaign) => campaign.active).length;
  }

  get inactiveCampaignsCount(): number {
    return this.campaigns.length - this.activeCampaignsCount;
  }

  get campaignsWithAssetsCount(): number {
    return this.campaigns.filter((campaign) => campaign.story && campaign.feed && campaign.banner).length;
  }

  get isCampaignFormValid(): boolean {
    return Boolean(
      this.campaignForm.name.trim() &&
        this.campaignForm.hook.trim() &&
        this.campaignForm.story.trim() &&
        this.campaignForm.feed.trim() &&
        this.campaignForm.banner.trim()
    );
  }

  get previewBenefits(): string[] {
    const benefits = (this.campaignForm.benefits || '')
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean)
      .slice(0, 4);
    return benefits.length ? benefits : ['Story', 'Feed', 'Banner'];
  }

  get previewCampaign(): {
    badge: string;
    title: string;
    accent: string;
    tail: string;
    description: string;
    primaryCta: string;
    secondaryCta: string;
    image: string;
    hook: string;
  } {
    return {
      badge: this.campaignForm.heroBadge.trim() || 'Campana activa',
      title: this.campaignForm.heroTitle.trim() || this.campaignForm.name.trim() || 'Nueva',
      accent: this.campaignForm.heroAccent.trim() || 'campana',
      tail: this.campaignForm.heroTail.trim() || 'lista para compartir',
      description:
        this.campaignForm.heroDescription.trim() ||
        this.campaignForm.description.trim() ||
        'Configura el mensaje principal, CTAs y assets para tu red.',
      primaryCta: this.campaignForm.ctaPrimaryText.trim() || 'Activar campana',
      secondaryCta: this.campaignForm.ctaSecondaryText.trim() || 'Ver materiales',
      image:
        this.campaignForm.heroImage.trim() ||
        this.campaignForm.banner.trim() ||
        this.campaignForm.feed.trim() ||
        this.campaignForm.story.trim(),
      hook: this.campaignForm.hook.trim() || 'Hook corto de la campana'
    };
  }

  editCampaign(campaign: AdminCampaign): void {
    this.clearCampaignAssets();
    this.campaignForm = {
      id: campaign.id,
      name: campaign.name,
      active: campaign.active,
      type: campaign.type ?? 'multinivel',
      hook: campaign.hook || '',
      description: campaign.description || '',
      story: campaign.story || '',
      feed: campaign.feed || '',
      banner: campaign.banner || '',
      heroImage: campaign.heroImage || '',
      heroBadge: campaign.heroBadge || '',
      heroTitle: campaign.heroTitle || '',
      heroAccent: campaign.heroAccent || '',
      heroTail: campaign.heroTail || '',
      heroDescription: campaign.heroDescription || '',
      ctaPrimaryText: campaign.ctaPrimaryText || '',
      ctaSecondaryText: campaign.ctaSecondaryText || '',
      benefits: (campaign.benefits ?? []).join(', ')
    };
    const assetFields: CampaignAssetField[] = ['story', 'feed', 'banner', 'heroImage'];
    assetFields.forEach((field) => {
      const url = campaign[field];
      if (url) {
        this.campaignAssetPreviews.set(field, url);
      }
    });
    this.campaignMessage = `Editando campana: ${campaign.name}.`;
  }

  updateCampaignField(field: CampaignFormField, value: string): void {
    this.campaignForm = {
      ...this.campaignForm,
      [field]: value
    };
  }

  resetCampaignForm(): void {
    this.campaignForm = this.getDefaultCampaignForm();
    this.campaignMessage = '';
    this.clearCampaignAssets();
  }

  uploadCampaignAsset(event: Event, field: CampaignAssetField): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      return;
    }
    const previewUrl = URL.createObjectURL(file);
    const current = this.campaignAssetPreviews.get(field);
    if (current?.startsWith('blob:')) {
      URL.revokeObjectURL(current);
    }
    this.campaignAssetPreviews.set(field, previewUrl);
    this.campaignAssetFiles.set(field, file);
    this.campaignAssetUploading.set(field, false);
  }

  clearCampaignAsset(field: CampaignAssetField): void {
    const preview = this.campaignAssetPreviews.get(field);
    if (preview?.startsWith('blob:')) {
      URL.revokeObjectURL(preview);
    }
    this.campaignAssetPreviews.delete(field);
    this.campaignAssetFiles.delete(field);
    this.campaignAssetUploading.delete(field);
    this.campaignForm = { ...this.campaignForm, [field]: '' };
  }

  private clearCampaignAssets(): void {
    this.campaignAssetPreviews.forEach((url) => {
      if (url.startsWith('blob:')) {
        URL.revokeObjectURL(url);
      }
    });
    this.campaignAssetPreviews.clear();
    this.campaignAssetFiles.clear();
    this.campaignAssetUploading.clear();
  }

  private uploadCampaignAssets(): Observable<Partial<Record<CampaignAssetField, string>>> {
    const entries = Array.from(this.campaignAssetFiles.entries());
    if (!entries.length) {
      return of({});
    }
    entries.forEach(([field]) => this.campaignAssetUploading.set(field, true));
    const uploads = entries.map(([field, file]) =>
      this.createAssetFromFile(file).pipe(
        switchMap((res) => {
          const url = res.asset?.url;
          return of({ field, url: url ?? '' });
        }),
        catchError(() => of({ field, url: '' })),
        finalize(() => this.campaignAssetUploading.set(field, false))
      )
    );
    return forkJoin(uploads).pipe(
      switchMap((results) => {
        const urls: Partial<Record<CampaignAssetField, string>> = {};
        results.forEach(({ field, url }) => {
          if (url) {
            urls[field] = url;
          }
        });
        return of(urls);
      })
    );
  }

  private createAssetFromFile(file: File): Observable<AssetResponse> {
    return this.readFileAsDataUrl(file).pipe(
      switchMap((dataUrl) => {
        const parts = dataUrl.split(',');
        const contentBase64 = parts.length >= 2 ? (parts[1] ?? '') : '';
        if (!contentBase64) {
          return of({ asset: { assetId: '' } } as AssetResponse);
        }
        const payload: CreateAssetPayload = {
          name: file.name,
          contentBase64,
          contentType: file.type || 'application/octet-stream'
        };
        return this.adminControl.createAsset(payload);
      })
    );
  }

  private readFileAsDataUrl(file: File): Observable<string> {
    return new Observable<string>((observer) => {
      const reader = new FileReader();
      reader.onload = () => {
        observer.next(String(reader.result ?? ''));
        observer.complete();
      };
      reader.onerror = () => {
        observer.error(new Error('No se pudo leer la imagen.'));
      };
      reader.readAsDataURL(file);
    });
  }

  saveCampaign(): void {
    if (this.isSavingCampaign || !this.isCampaignFormValid) {
      return;
    }

    const benefits = (this.campaignForm.benefits || '')
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean)
      .slice(0, 4);

    this.isSavingCampaign = true;
    this.uploadCampaignAssets()
      .pipe(
        switchMap((uploadedUrls) => {
          const story = uploadedUrls['story'] || this.campaignForm.story.trim();
          const feed = uploadedUrls['feed'] || this.campaignForm.feed.trim();
          const banner = uploadedUrls['banner'] || this.campaignForm.banner.trim();
          const heroImage = uploadedUrls['heroImage'] || this.campaignForm.heroImage.trim() || undefined;
          return this.adminControl.saveCampaign({
            id: this.campaignForm.id || undefined,
            name: this.campaignForm.name.trim(),
            active: this.campaignForm.active,
            type: this.campaignForm.type,
            hook: this.campaignForm.hook.trim(),
            description: this.campaignForm.description.trim() || undefined,
            story,
            feed,
            banner,
            heroImage,
            heroBadge: this.campaignForm.heroBadge.trim() || undefined,
            heroTitle: this.campaignForm.heroTitle.trim() || undefined,
            heroAccent: this.campaignForm.heroAccent.trim() || undefined,
            heroTail: this.campaignForm.heroTail.trim() || undefined,
            heroDescription: this.campaignForm.heroDescription.trim() || undefined,
            ctaPrimaryText: this.campaignForm.ctaPrimaryText.trim() || undefined,
            ctaSecondaryText: this.campaignForm.ctaSecondaryText.trim() || undefined,
            benefits
          });
        }),
        finalize(() => (this.isSavingCampaign = false))
      )
      .subscribe({
        next: (campaign) => {
          this.campaignMessage = `Campana guardada: ${campaign.name}.`;
          this.campaignForm = this.getDefaultCampaignForm();
          this.clearCampaignAssets();
        },
        error: () => {
          this.campaignMessage = 'No se pudo guardar la campana.';
        }
      });
  }

  private getDefaultCampaignForm(): {
    id: string;
    name: string;
    active: boolean;
    type: 'multinivel' | 'producto';
    hook: string;
    description: string;
    story: string;
    feed: string;
    banner: string;
    heroImage: string;
    heroBadge: string;
    heroTitle: string;
    heroAccent: string;
    heroTail: string;
    heroDescription: string;
    ctaPrimaryText: string;
    ctaSecondaryText: string;
    benefits: string;
  } {
    return {
      id: '',
      name: '',
      active: true,
      type: 'multinivel',
      hook: '',
      description: '',
      story: '',
      feed: '',
      banner: '',
      heroImage: '',
      heroBadge: '',
      heroTitle: '',
      heroAccent: '',
      heroTail: '',
      heroDescription: '',
      ctaPrimaryText: '',
      ctaSecondaryText: '',
      benefits: ''
    };
  }
}
