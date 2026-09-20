CREATE TABLE `audit` (
	`id` text PRIMARY KEY NOT NULL,
	`userId` text NOT NULL,
	`action` text NOT NULL,
	`reason` text NOT NULL,
	`createdAt` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `bans` (
	`userId` text PRIMARY KEY NOT NULL,
	`reason` text NOT NULL,
	`until` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `limits` (
	`id` text PRIMARY KEY NOT NULL,
	`count` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `messages` (
	`id` text PRIMARY KEY NOT NULL,
	`roomId` text NOT NULL,
	`userId` text NOT NULL,
	`author` text NOT NULL,
	`body` text NOT NULL,
	`kind` text NOT NULL,
	`createdAt` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `messages_room_date` ON `messages` (`roomId`,`createdAt`);--> statement-breakpoint
CREATE TABLE `posts` (
	`id` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`body` text NOT NULL,
	`translation` text DEFAULT '' NOT NULL,
	`language` text NOT NULL,
	`source` text NOT NULL,
	`url` text NOT NULL,
	`publishedAt` text NOT NULL,
	`collectedAt` text NOT NULL,
	`sentiment` text DEFAULT 'unknown' NOT NULL,
	`stance` text DEFAULT '미분류' NOT NULL,
	`contentHash` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `posts_url` ON `posts` (`url`);--> statement-breakpoint
CREATE UNIQUE INDEX `posts_hash` ON `posts` (`contentHash`);--> statement-breakpoint
CREATE INDEX `posts_lang_date` ON `posts` (`language`,`publishedAt`);--> statement-breakpoint
CREATE TABLE `reports` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`title` text NOT NULL,
	`payload` text NOT NULL,
	`createdAt` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `reports_owner` ON `reports` (`owner`,`createdAt`);--> statement-breakpoint
CREATE TABLE `rooms` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`title` text NOT NULL,
	`reportId` text NOT NULL,
	`createdAt` text NOT NULL,
	`closed` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE INDEX `rooms_date` ON `rooms` (`createdAt`);