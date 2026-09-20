import {wrap,db} from '@/lib/server';
import {getChatGPTUser} from '@/app/chatgpt-auth';
export const GET=wrap(async()=>{const [sources,languageCounts]=await Promise.all([db().prepare('SELECT source,COUNT(*) AS count FROM posts GROUP BY source').all(),db().prepare('SELECT language,COUNT(*) AS count FROM posts GROUP BY language').all()]);const u=await getChatGPTUser();return Response.json({sources:sources.results,languageCounts:languageCounts.results,user:u?{id:u.userId}:null},{headers:{'Cache-Control':'private, no-store'}})});
