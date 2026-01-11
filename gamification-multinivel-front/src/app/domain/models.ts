export interface UserProfile {
  /** Unique identifier for the user profile. */
  id: string;
  /** Display name shown in the experience. */
  displayName: string;
  /** Optional URL for the user's avatar image. */
  avatarUrl?: string;
  /** Current level achieved by the user. */
  level: number;
  /** Total points accumulated across activities. */
  totalPoints: number;
  /** Position of the user in the ranking leaderboard. */
  rank: number;
}

export interface Goal {
  /** Unique identifier for the goal. */
  id: string;
  /** Short label to describe the goal. */
  title: string;
  /** Target amount the user needs to reach. */
  targetAmount: number;
  /** Current amount achieved toward the target. */
  currentAmount: number;
  /** Message shown for what remains to complete the goal. */
  remainingMessage: string;
  /** Optional date when the goal is due. */
  dueDate?: string;
}

export interface NextAction {
  /** Unique identifier for the action. */
  id: string;
  /** Label shown to the user for the next action. */
  label: string;
  /** Short description to guide the user. */
  description: string;
  /** Points awarded when the action is completed. */
  rewardPoints: number;
  /** Indicates whether the action has been completed. */
  completed: boolean;
}

export interface Metrics {
  /** Total impact points generated in the current period. */
  impactPoints: number;
  /** Total progress points earned in the current period. */
  progressPoints: number;
  /** Number of new members added in the current period. */
  newMembers: number;
  /** Conversion rate for the current period expressed as a percentage. */
  conversionRate: number;
}

export interface Mission {
  /** Unique identifier for the mission. */
  id: string;
  /** Title of the mission shown in the UI. */
  title: string;
  /** Description that explains mission requirements. */
  description: string;
  /** Progress value from 0 to 100 for the mission. */
  progressPercent: number;
  /** Points or rewards granted upon completion. */
  rewardPoints: number;
  /** Current status of the mission. */
  status: 'pending' | 'active' | 'completed';
}

export interface Achievement {
  /** Unique identifier for the achievement. */
  id: string;
  /** Title displayed for the achievement. */
  title: string;
  /** Description of the achievement criteria. */
  description: string;
  /** Optional URL to the badge image. */
  badgeUrl?: string;
  /** ISO timestamp for when the achievement was unlocked. */
  unlockedAt?: string;
}

export interface Order {
  /** Unique identifier for the order. */
  id: string;
  /** Total points associated with the activity. */
  impactPoints: number;
  /** ISO timestamp representing when the order was placed. */
  createdAt: string;
  /** Status of the order lifecycle. */
  status: 'pending' | 'paid' | 'fulfilled' | 'cancelled';
  /** Identifier for the customer who placed the order. */
  customerId: string;
}

export interface Commission {
  /** Unique identifier for the recognition entry. */
  id: string;
  /** Points earned for the recognition. */
  rewardPoints: number;
  /** Percentage rate applied to calculate the recognition. */
  contributionPercent: number;
  /** Associated order identifier that generated the recognition. */
  orderId: string;
  /** ISO timestamp for when the recognition was earned. */
  earnedAt: string;
  /** Status of the recognition review. */
  status: 'pending' | 'paid' | 'cancelled';
}

export interface NetworkMember {
  /** Unique identifier for the network member. */
  id: string;
  /** Display name for the member. */
  name: string;
  /** Current level or tier of the member. */
  level: number;
  /** ISO date when the member joined the network. */
  joinedAt: string;
  /** Indicates whether the member is active. */
  active: boolean;
}

export interface Landing {
  /** Primary headline shown on the landing experience. */
  heroTitle: string;
  /** Supporting subtitle shown under the hero title. */
  heroSubtitle: string;
  /** URL for the hero image asset. */
  heroImageUrl: string;
  /** Alternative text describing the hero image. */
  heroImageAlt: string;
  /** Label for the primary call-to-action button. */
  ctaLabel: string;
  /** Target URL for the call-to-action. */
  ctaUrl: string;
  /** Highlights shown as bullet points or cards. */
  highlights: string[];
}

export interface AuthCoachMessage {
  /** Unique identifier for the coach message. */
  id: string;
  /** Short headline that names the guidance from the coach. */
  title: string;
  /** Message body shown inline near the auth form. */
  body: string;
}

export interface AuthContext {
  /** Main headline for the authentication view. */
  title: string;
  /** Supporting subtitle under the headline. */
  subtitle: string;
  /** Helper text reassuring the user about the flow. */
  helperText: string;
  /** Label for the primary submit action. */
  primaryActionLabel: string;
  /** Label for the secondary submit action. */
  secondaryActionLabel: string;
  /** Inline guidance from the coach. */
  coachMessages: AuthCoachMessage[];
}

export type UserRole = 'public' | 'user' | 'admin';

export interface AuthSession {
  /** Auth token assigned by the mock service. */
  token: string;
  /** Role assigned to the authenticated user. */
  role: UserRole;
  /** Email for the signed-in account. */
  email: string;
  /** Unix timestamp in milliseconds when the session expires. */
  expiresAt: number;
}
