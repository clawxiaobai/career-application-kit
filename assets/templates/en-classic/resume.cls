% resume.cls - minimal one-page English resume class (XeLaTeX)
% Original, written for career-application-kit. MIT licensed.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{resume}[2026/01/01 Minimal resume class]
\LoadClass[10pt]{article}

\RequirePackage{fontspec}
\RequirePackage{xifthen}
\RequirePackage{hyperref}
\RequirePackage{url}
\RequirePackage{xcolor}
\RequirePackage{titlesec}
\RequirePackage{enumitem}
\RequirePackage[
  a4paper,
  left=0.60in,
  right=0.60in,
  top=0.60in,
  bottom=0.60in,
  nohead
]{geometry}

\setlength{\parindent}{0pt}
\setlist[itemize]{topsep=0.15em, leftmargin=1.25pc, itemsep=0pt, parsep=0pt}
\urlstyle{same}
\hypersetup{hidelinks}

\titleformat{\section}
  {\large\bfseries\raggedright}
  {}{0em}{}[\titlerule]
\titlespacing*{\section}{0cm}{*1.0}{*1.0}

\titleformat{\subsection}
  {\normalsize\bfseries\raggedright}
  {}{0em}{}
\titlespacing*{\subsection}{0cm}{*1.0}{*0.6}

\newcommand{\datedsection}[2]{\section[#1]{#1 \hfill #2}}
\newcommand{\datedsubsection}[2]{\subsection[#1]{#1 \hfill #2}}
\newcommand{\datedline}[2]{\par #1 \hfill #2 \par}

\newcommand{\name}[1]{{\Huge\bfseries #1}\par\vspace{0.6ex}}
\newcommand{\email}[1]{\href{mailto:#1}{#1}}
\newcommand{\phone}[1]{#1}
\newcommand{\wechat}[1]{WeChat: #1}
\newcommand{\github}[2][]{\href{#2}{\ifthenelse{\isempty{#1}}{#2}{#1}}}
\newcommand{\linkedin}[2][]{\href{#2}{\ifthenelse{\isempty{#1}}{#2}{#1}}}
\newcommand{\homepage}[2][]{\href{#2}{\ifthenelse{\isempty{#1}}{#2}{#1}}}
\newcommand{\basicInfo}[1]{\centerline{\small #1}}
\newcommand{\role}[2]{\par (#1) \textit{#2} \par}
\newcommand{\rolewithdate}[3]{(#1) \textit{#2} \hfill #3}
