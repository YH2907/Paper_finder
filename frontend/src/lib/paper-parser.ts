/**
 * 论文引用解析器
 * 从 AI 回复中提取论文引用信息，用于在聊天界面中显示可点击的论文卡片
 */

export interface ParsedPaperRef {
  /** 论文标题（如果能提取到） */
  title?: string;
  /** 论文 URL */
  url: string;
  /** 在原文中的位置 */
  start: number;
  end: number;
}

/**
 * 从 AI 消息文本中提取论文引用
 * 支持以下格式：
 * 1. Markdown 链接: [标题](url)
 * 2. 直接 URL: https://arxiv.org/abs/XXXX.XXXXX
 * 3. 带标题的 URL 引用
 */
export function parsePaperRefs(text: string): ParsedPaperRef[] {
  const refs: ParsedPaperRef[] = [];
  const seenUrls = new Set<string>();

  // 1. 匹配 Markdown 链接中的论文 URL
  const markdownLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
  let match;
  while ((match = markdownLinkRegex.exec(text)) !== null) {
    const url = match[2];
    if (!seenUrls.has(url)) {
      refs.push({
        title: match[1],
        url,
        start: match.index,
        end: match.index + match[0].length,
      });
      seenUrls.add(url);
    }
  }

  // 2. 匹配直接的论文 URL（仅学术域名）
  const ACADEMIC_DOMAINS = [
    'arxiv.org', 'doi.org', 'semanticscholar.org', 'openreview.net',
    'aclanthology.org', 'proceedings.mlr.press', 'ieee.org', 'ieeexplore.ieee.org',
    'acm.org', 'dl.acm.org', 'springer.com', 'nature.com', 'sciencedirect.com',
    'papers.nips.cc', 'proceedings.neurips.cc', 'researchgate.net',
  ];
  const urlRegex = /(https?:\/\/[^\s\)\]，。、；："'"'）】\u4e00-\u9fa5]+)/g;
  while ((match = urlRegex.exec(text)) !== null) {
    const url = match[1];
    const isAcademic = ACADEMIC_DOMAINS.some(d => url.includes(d));
    if (isAcademic && !seenUrls.has(url)) {
      refs.push({
        url,
        start: match.index,
        end: match.index + match[0].length,
      });
      seenUrls.add(url);
    }
  }

  // 3. 匹配 arXiv 编号（例如：arXiv:2401.12345 或 arxiv 2401.12345）
  const arxivIdRegex = /\barxiv\s*[:：]?\s*(\d{4}\.\d{4,5})(v\d+)?\b/gi;
  while ((match = arxivIdRegex.exec(text)) !== null) {
    const id = `${match[1]}${match[2] || ""}`;
    const url = `https://arxiv.org/abs/${id}`;
    if (!seenUrls.has(url)) {
      refs.push({
        title: `arXiv:${id}`,
        url,
        start: match.index,
        end: match.index + match[0].length,
      });
      seenUrls.add(url);
    }
  }

  // 4. 匹配裸 DOI（例如：10.1145/3544548.3581365）
  const doiRegex = /\b(10\.\d{4,9}\/[-._;()\/:A-Z0-9]+)\b/gi;
  while ((match = doiRegex.exec(text)) !== null) {
    const doi = match[1];
    const url = `https://doi.org/${doi}`;
    if (!seenUrls.has(url)) {
      refs.push({
        title: `DOI: ${doi}`,
        url,
        start: match.index,
        end: match.index + match[0].length,
      });
      seenUrls.add(url);
    }
  }

  // 5. 兜底：从“推荐论文标题列表”里提取标题，并生成可跳转的检索链接
  // 典型格式：
  // 1. **Paper Title**
  // 2. Paper Title
  // - **Paper Title**
  const titleLineRegex = /(?:^|\n)\s*(?:\d+[\.)]|[-*•])\s*(?:\*\*([^*\n]{8,220})\*\*|([^\n]{8,220}))/g;
  while ((match = titleLineRegex.exec(text)) !== null) {
    const rawTitle = (match[1] || match[2] || "").trim();
    const title = rawTitle
      .replace(/^['"《]+|['"》]+$/g, "")
      .replace(/\s{2,}/g, " ");

    if (!isLikelyPaperTitle(title)) {
      continue;
    }

    const url = `https://www.bing.com/search?q=${encodeURIComponent(title + " paper")}`;
    if (!seenUrls.has(url)) {
      refs.push({
        title,
        url,
        start: match.index,
        end: match.index + match[0].length,
      });
      seenUrls.add(url);
    }
  }

  refs.sort((a, b) => a.start - b.start);

  return refs;
}

function isLikelyPaperTitle(title: string): boolean {
  if (!title || title.length < 8) return false;

  const lower = title.toLowerCase();
  const rejectKeywords = [
    "推荐理由",
    "摘要",
    "作者",
    "发表",
    "关键词",
    "研究方向",
    "总结",
    "结论",
    "说明",
    "注意",
    "建议",
    "question",
    "answer",
  ];

  if (rejectKeywords.some((kw) => lower.includes(kw))) {
    return false;
  }

  const hasTooManyPunctuation = (title.match(/[，。！？；：]/g) || []).length >= 3;
  if (hasTooManyPunctuation) {
    return false;
  }

  // 论文标题通常包含多个单词或较长短语
  const wordCount = title.split(/\s+/).filter(Boolean).length;
  return wordCount >= 3 || title.length >= 18;
}

/**
 * 判断 URL 是否为论文相关链接
 */
/**
 * 提取消息中的论文 ID（arxiv ID 等）
 */
export function extractPaperId(url: string): string | null {
  // arxiv.org/abs/XXXX.XXXXX
  const arxivMatch = url.match(/arxiv\.org\/abs\/(\d+\.\d+)/);
  if (arxivMatch) return arxivMatch[1];

  // arxiv.org/pdf/XXXX.XXXXX
  const arxivPdfMatch = url.match(/arxiv\.org\/pdf\/(\d+\.\d+)/);
  if (arxivPdfMatch) return arxivPdfMatch[1];

  // 通用 DOI 格式
  const doiMatch = url.match(/doi\.org\/(.+)/);
  if (doiMatch) return doiMatch[1];

  return null;
}
