---
layout: about
title: about
permalink: /
subtitle: Full Professor of Computer Science, <a href="https://www.cs.manchester.ac.uk/">University of Manchester</a>. Director, <a href="https://www.cs.manchester.ac.uk/arm-coe/">Arm Centre of Excellence</a>.

profile:
  align: right
  image: prof_pic.jpg
  image_circular: false
  more_info: >
    <p>Department of Computer Science</p>
    <p>Kilburn Building, Oxford Road</p>
    <p>Manchester M13 9PL, UK</p>

selected_papers: true
social: true

announcements:
  enabled: true
  scrollable: true
  limit: 5

latest_posts:
  enabled: false
---

**[Lucas C. Cordeiro](https://research.manchester.ac.uk/en/persons/lucas.cordeiro)** is a Full Professor in the [Department of Computer Science](https://www.cs.manchester.ac.uk/) (CS) at the [University of Manchester](https://www.manchester.ac.uk/) (UoM), where he leads the [Systems and Software Security (S3) Research Group](https://www.cs.manchester.ac.uk/research/expertise/systems-and-software-security/). Prof. Cordeiro is also the Business Engagement and Innovation Director in the CS department and the [Arm Centre of Excellence](https://www.cs.manchester.ac.uk/arm-coe/) Director at UoM. In addition, he is affiliated with the [Trusted Digital Systems Cluster](https://www.socialsciences.manchester.ac.uk/dts/research/clusters/trusted-digital-systems/) at the Centre for Digital Trust and Society, the [Formal Methods Group](https://www.cs.manchester.ac.uk/research/expertise/formal-methods/) at UoM, and the Post-Graduate Programs in Electrical Engineering ([PPGEE](https://ppgee.ufam.edu.br/docentes.html)) and Informatics ([PPGI](https://ppgi.ufam.edu.br/docentes.html)) at the Federal University of Amazonas, Brazil. He is the Chief Technology Officer at [VeriBee](https://www.veribee.co/), a spinout from the University of Manchester that aims to revolutionize the software testing/verification market; he is the Scientific Lead Advisor at [ByteRepair](https://byterepair.io/), a University of Manchester spinout applying formal verification to automated code security analysis and repair, and a member of the technical advisory board at [Axiomise](https://www.axiomise.com/technical-advisory-board/). Before joining the University of Manchester, he worked as a post-doctoral researcher at the University of Oxford and as a research engineer at Diffblue. In addition, Dr. Cordeiro worked for five years as a software engineer at Siemens / BenQ Mobile and CTPIM / NXP semiconductors. He also leads the Software Security and Automated Reasoning theme in the Advanced Computer Science MSc programme at UoM. His work focuses on software model checking, automated testing, program synthesis, software security, embedded and cyber-physical systems, and, more recently, on combining formal methods with large language models. He has co-authored more than 190 peer-reviewed publications in the most prestigious venues (e.g., ICSE, CAV, TACAS, FSE, ASE, ISSTA, TSE, TR, TC), comprising 44 journal articles, 148 conference and workshop papers, one edited book, and four book chapters, with an h-index of 36. He has received various international awards, including an Amazon Research Award in Automated Reasoning (Fall 2025), the Most Influential Paper Award at ASE’23, ACM SIGSOFT Distinguished Paper Awards at ICSE’11 and ASE’24, the Best Tool Paper Award at SBSeg’23, best paper awards at SBESC’15 and SAC’08, and 56 medals from the international competitions on software verification (SV-COMP) and testing (Test-Comp) from 2012 to 2026. He has a proven track record of securing research funding from Amazon, BAE Systems, British Council, CNPq, EPSRC, the European Commission, FAPEAM, GCHQ, Innovate UK, Intel, Motorola, Nokia Institute of Technology, the Royal Society, Samsung, and UKRI (career total over USD 16.4M). He has supervised 13 PhD theses, three MPhil dissertations, and 30 MSc dissertations. [Full CV](https://ssvlab.github.io/lucasccordeiro/cv/cordeiro-cv.pdf)

His publication list is also indexed by [DBLP](https://dblp.org/pid/42/4311.html),
the [ACM Author Profile](http://portal.acm.org/author_page.cfm?id=81330489584&coll=&dl=GUIDE&trk=0),
[SCOPUS](http://www.scopus.com/authid/detail.url?authorId=24328704500),
[Web of Science](https://www.webofscience.com/wos/author/record/47022616) and
[Google Scholar](https://scholar.google.com/citations?user=Lje1SFgAAAAJ&hl=en&oi=ao).

<!-- The legacy single-page site addressed its sections by fragment. Bookmarks
     and citations using those fragments still land here, so forward them to the
     page that now holds that content. Unknown fragments are left alone. -->
<script>
  (function () {
    var moved = {
      news: "news", grants: "grants", awards: "awards", publications: "publications",
      supervisions: "supervisions", tools: "tools", courses: "courses"
    };
    var target = moved[window.location.hash.replace(/^#/, "")];
    if (target) {
      window.location.replace("{{ site.baseurl }}/" + target + "/");
    }
  })();
</script>
