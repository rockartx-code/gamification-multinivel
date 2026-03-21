import { Injectable } from '@angular/core';

import {
  DashboardCampaign,
  DashboardProduct,
  FeaturedItem
} from '../models/user-dashboard.model';

export type UserDashboardSocialChannel = 'whatsapp' | 'instagram' | 'facebook';
export type UserDashboardSocialFormat = 'story' | 'feed' | 'banner';

type ShareTemplateInput = {
  channel: UserDashboardSocialChannel;
  activeFeatured: FeaturedItem;
  referralLink: string;
  products: DashboardProduct[];
};

@Injectable({ providedIn: 'root' })
export class UserDashboardShareService {
  private readonly fixedFeatured: FeaturedItem[] = [
    {
      id: 'fixed-familia',
      label: 'Familia',
      hook: 'Programa familiar',
      story: 'images/L-Programa3.png',
      feed: 'images/L-Programa3.png',
      banner: 'images/L-Programa3.png'
    },
    {
      id: 'fixed-entrenador',
      label: 'Entrenador',
      hook: 'Programa entrenador',
      story: 'images/L-Programa2.png',
      feed: 'images/L-Programa2.png',
      banner: 'images/L-Programa2.png'
    }
  ];

  buildFeaturedCarousel(
    featured: FeaturedItem[],
    products: DashboardProduct[],
    campaigns: DashboardCampaign[]
  ): FeaturedItem[] {
    const featuredIds = new Set(featured.map((item) => item.id));
    const campaignItems: FeaturedItem[] = campaigns
      .filter((campaign) => campaign.active !== false)
      .map((campaign) => ({
        id: `campaign:${campaign.id}`,
        label: campaign.name,
        hook: campaign.hook || campaign.heroDescription || 'Campana especial',
        story: campaign.story || campaign.heroImage || '',
        feed: campaign.feed || campaign.heroImage || '',
        banner: campaign.banner || campaign.heroImage || ''
      }));
    const productItems: FeaturedItem[] = products
      .filter((product) => !featuredIds.has(product.id))
      .map((product) => ({
        id: product.id,
        label: product.name,
        hook: product.badge || 'Producto destacado',
        story: product.img || '',
        feed: product.img || '',
        banner: product.img || ''
      }));

    return [...this.fixedFeatured, ...featured, ...campaignItems, ...productItems];
  }

  getSocialFormatLabel(format: UserDashboardSocialFormat): string {
    if (format === 'feed') {
      return 'Feed (1:1)';
    }
    if (format === 'banner') {
      return 'Banner (16:9)';
    }
    return 'Story (9:16)';
  }

  getSocialAspectRatio(format: UserDashboardSocialFormat): string {
    if (format === 'feed') {
      return '1/1';
    }
    if (format === 'banner') {
      return '16/9';
    }
    return '9/16';
  }

  getActiveSocialAsset(format: UserDashboardSocialFormat, activeFeatured: FeaturedItem): string {
    if (format === 'feed') {
      return activeFeatured.feed || '';
    }
    if (format === 'banner') {
      return activeFeatured.banner || '';
    }
    return activeFeatured.story || '';
  }

  buildAutoCaption(input: ShareTemplateInput): string {
    const label = input.activeFeatured.label || 'Producto destacado';
    const hook = input.activeFeatured.hook || 'Descubre por que a todos les funciona.';
    const productCopy = this.getActiveProductCopy(input.channel, input.activeFeatured.id, input.products);
    const cta = `Pidelo aqui: ${input.referralLink}`;
    if (productCopy) {
      return `${productCopy}\n\n${cta}`;
    }
    return `${label}: ${hook}\n\nComo lo uso: ...\n\n${cta}`;
  }

  buildChannelTemplate(input: ShareTemplateInput): string {
    const label = input.activeFeatured.label;
    const hook = input.activeFeatured.hook;
    const productCopy = this.getActiveProductCopy(input.channel, input.activeFeatured.id, input.products);
    let cta = `Pidelo aqui: ${input.referralLink}`;
    let opener = 'Te comparto esto:';
    let howTo = productCopy || 'Como lo uso: ...';

    switch (input.channel) {
      case 'whatsapp':
        opener = 'Te lo paso por WhatsApp:';
        howTo = productCopy || 'Resumen rapido: ...';
        cta = `Si te interesa, responde y te paso el link: ${input.referralLink}`;
        break;
      case 'instagram':
        opener = 'Tip rapido para Instagram:';
        howTo = productCopy || 'Como lo uso: ...';
        cta = `Pide el link por DM o en bio: ${input.referralLink}`;
        break;
      case 'facebook':
        opener = 'Comparte esto en Facebook:';
        howTo = productCopy || 'Mi experiencia: ...';
        cta = `Escribeme por inbox y te paso el link: ${input.referralLink}`;
        break;
    }

    return `${opener}\n\n${label}: ${hook}\n\n${howTo}\n\n${cta}`;
  }

  getActiveProductCopy(
    channel: UserDashboardSocialChannel,
    featuredId: string | undefined,
    products: DashboardProduct[]
  ): string {
    const product = featuredId ? products.find((item) => item.id === featuredId) : null;
    if (!product) {
      return '';
    }
    if (channel === 'facebook') {
      return (product.copyFacebook || '').trim();
    }
    if (channel === 'instagram') {
      return (product.copyInstagram || '').trim();
    }
    return (product.copyWhatsapp || '').trim();
  }
}
