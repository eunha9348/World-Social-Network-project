CREATE TABLE `profiles` (
	`userId` text PRIMARY KEY NOT NULL,
	`displayName` text DEFAULT '' NOT NULL,
	`language` text DEFAULT 'ko' NOT NULL,
	`updatedAt` text NOT NULL
);
