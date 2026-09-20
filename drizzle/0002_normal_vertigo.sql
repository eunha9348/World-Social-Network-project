ALTER TABLE `posts` ADD `authorName` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `authorHandle` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `authorUrl` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `followers` integer;--> statement-breakpoint
ALTER TABLE `posts` ADD `profession` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `professionEvidenceUrl` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `authorEvidenceUrl` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `authorObservedAt` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `posts` ADD `metadataVerified` integer DEFAULT 0 NOT NULL;