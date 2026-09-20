import {db,ApiError} from './server';
import {demoPosts} from './demo';
import type {Post} from './types';
export async function evidence(ids:string[],demo=false){if(demo){const p=demoPosts.filter(p=>ids.includes(p.id));if(p.length!==ids.length)throw new ApiError(400,'예시 게시글 선택을 확인해 주세요.');return p}const p=(await db().prepare(`SELECT * FROM posts WHERE id IN (${ids.map(()=>'?').join(',')})`).bind(...ids).all<Post>()).results;if(p.length!==ids.length)throw new ApiError(404,'일부 게시글이 삭제되었습니다. 검색을 갱신해 주세요.');return p}
