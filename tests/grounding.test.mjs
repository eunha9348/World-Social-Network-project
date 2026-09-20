import fs from 'node:fs';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function load(name){const code=ts.transpileModule(fs.readFileSync(new URL('../lib/'+name+'.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;return import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))}
const {validateCitations,validateMessageQuotes}=await load('grounding');
const {rankEvidence,provenanceScore}=await load('provenance');
const {groundedReport}=await load('grounded-report');
const p={id:'a',body:'This is an exact original statement with enough length.',source:'Example',url:'https://example.com/a',language:'en',title:'Example'};
assert.equal(validateCitations([{sourceId:'a',quote:'exact original statement'}],[p]).length,1);
assert.throws(()=>validateCitations([{sourceId:'fake',quote:'exact original statement'}],[p]));
assert.throws(()=>validateCitations([{sourceId:'a',quote:'This invented statement is false.'}],[p]));
assert.throws(()=>validateCitations([],[p]));
assert.throws(()=>validateMessageQuotes([{messageId:'fake',quote:'exact original statement'}],[{...p,author:'A',kind:'human'}]));
assert.equal(provenanceScore({...p,followers:999999999}),30);
const verified={...p,id:'b',authorName:'B',authorUrl:'https://example.com/B',authorEvidenceUrl:'https://example.com/evidence',authorObservedAt:'2026-09-15',metadataVerified:1};
assert.equal(rankEvidence([{...p,followers:999999999},verified])[0].id,'b');
assert.equal(rankEvidence(Array.from({length:5},(_,i)=>({...verified,id:String(i)}))).length,2);
const report=groundedReport('Topic',[p],1);assert.equal(report.pages.length,1);assert.ok(report.pages[0].text.includes(p.body));assert.deepEqual(report.sources,[p]);assert.throws(()=>groundedReport('Topic',[],1));
console.log('Grounding, fabricated citation rejection, provenance and author diversity checks passed.');
