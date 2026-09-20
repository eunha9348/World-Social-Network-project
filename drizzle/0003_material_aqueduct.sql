CREATE TABLE `translations` (
	`id` text PRIMARY KEY NOT NULL,
	`postId` text NOT NULL,
	`targetLanguage` text NOT NULL,
	`title` text NOT NULL,
	`body` text NOT NULL,
	`contentHash` text NOT NULL,
	`model` text NOT NULL,
	`createdAt` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `translations_post_target` ON `translations` (`postId`,`targetLanguage`);--> statement-breakpoint
CREATE INDEX `translations_created` ON `translations` (`createdAt`);