import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiKpiCardComponent } from '../../../components/ui-kpi-card/ui-kpi-card.component';
import { AdminCampaign } from '../../../models/admin.model';
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
  | 'benefits';

@Component({
  selector: 'app-admin-campaigns',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent, UiKpiCardComponent],
  templateUrl: './admin-campaigns.component.html'
})
export class AdminCampaignsComponent {
  @Input() campaigns: AdminCampaign[] = [];

  campaignMessage = '';
  isSavingCampaign = false;
  campaignForm = this.getDefaultCampaignForm();

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
    this.campaignForm = {
      id: campaign.id,
      name: campaign.name,
      active: campaign.active,
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
    this.adminControl
      .saveCampaign({
        id: this.campaignForm.id || undefined,
        name: this.campaignForm.name.trim(),
        active: this.campaignForm.active,
        hook: this.campaignForm.hook.trim(),
        description: this.campaignForm.description.trim() || undefined,
        story: this.campaignForm.story.trim(),
        feed: this.campaignForm.feed.trim(),
        banner: this.campaignForm.banner.trim(),
        heroImage: this.campaignForm.heroImage.trim() || undefined,
        heroBadge: this.campaignForm.heroBadge.trim() || undefined,
        heroTitle: this.campaignForm.heroTitle.trim() || undefined,
        heroAccent: this.campaignForm.heroAccent.trim() || undefined,
        heroTail: this.campaignForm.heroTail.trim() || undefined,
        heroDescription: this.campaignForm.heroDescription.trim() || undefined,
        ctaPrimaryText: this.campaignForm.ctaPrimaryText.trim() || undefined,
        ctaSecondaryText: this.campaignForm.ctaSecondaryText.trim() || undefined,
        benefits
      })
      .pipe(finalize(() => (this.isSavingCampaign = false)))
      .subscribe({
        next: (campaign) => {
          this.campaignMessage = `Campana guardada: ${campaign.name}.`;
          this.campaignForm = this.getDefaultCampaignForm();
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
