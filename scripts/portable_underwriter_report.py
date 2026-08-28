# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy",
#   "pandas",
#   "plotly>=6.9",
#   "pyarrow>=23.0.1",
# ]
# ///
"""Portable, prediction-only underwriter model review.

Copy this file anywhere and run it with ``uv run`` or import ``build_report``.
It contains the model-neutral report runtime and has no repository dependency.
"""

from __future__ import annotations

import argparse
import base64 as _base64
import sys as _sys
import tomllib
import types as _types
import zlib as _zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

SOURCE_SHA256 = "1c5a734b07150925008cd6decfe556063c77170b6e9a36ae0df855b28cff347c"
_RUNTIME_PREFIX = "_portable_underwriter_1c5a734b0715"
# fmt: off
_EMBEDDED_SOURCES = {
    '_portable_underwriter_1c5a734b0715.reporting._underwriter_styles': (
        'c-'
        'pmF{ch{F75_g^!6hgVca|s1A2)H(VO!B*16FM4?fw{wqM#+pW+O`iCC5&SzQ!JB53?uPIsA}FigJ?MtQXCVk16te'
        '{>}$=udlDaVRa?is5+G_BVT^}NNT|kyyZ`<A$cW8yJw_nX_?WYDj7MJ851YLTPDa~zWw@dv+L{YtE+Fm`p4hD`Sy'
        'oD{qf^hKj0o;5P|fKsH&Fyd__oF6_tpZbk7cKLkhmzw+}#$qU~-'
        '&Zt@TLT}~CDrX?$oCjV2kmYrK5&GTfD+$qxG*s=_0>(x5@u-1E30+<707H1zaW)q{P6;+96-'
        'KF=dd%f>YaM(law)A$sjHhJ2yoVnv_z};NWTH1Hj==Iwe80ZWXitioDo3WWEu*<UOGuWod9qCO36-'
        'Gb4j<p<YZ@nt_{@r;I-'
        '!iqY_VcC(UReg&SSkxUZuyz<DuEp3^$S7FXmISSWO8E5zppp&3bbbIZfgCCn|2WYTd8k?`>NkgZa9*fuI>bHc@lf'
        'kY#;#Xa|sRZD>u6Tg<Ihijr)|ol9A4$UJdLOCWVS@v^B|+JcXqc-HPWWU-F%yI-'
        '!ZKA)1$H=8X3XJqnMnxpgmOt#fIYWPna&8n>oqz3}e?At>j{qDd^vt#_AKkpg3ADkY?pCN5a)5o2tz_X2_w!4Wud'
        'Rt}Ba+{1dbwQsuBrn+c;pKg^r#(_BIC>dDtQ^34;DM}7CH==^)AIZ|N~^MEB|MVCPbTC>RP1=EcdcobN%4&CswXC'
        'L={xk;Ru`Dp5oc%^K$4nQc-'
        '(wZpMN)>ElEV{x&SA5Zh*%r`BTBm$FFJnQGWh2teukUk8D>l^3T6sPf0^d@Cqh)uGDjE+o}XIE5LSB!pr&y;jRzi'
        '<sMeH(jM+gsZyh@MXW^YWQ{?AiezG8UY|)*6+AN%O8TT<qMg%7+qv%~tRdI;N3{if8-'
        '8tj&sWIa__h<2SP8t@qruQst;IKt<w?G_R?!sUcCc*CvV37J11F^00#N#Ak{(5a{FYT4QN#_FJ&+2*inrjT@ocrS'
        ')V`7M5k2vS!{bveluwn$^NHWJbjtzp&tF`}*WbI}N-'
        'I{!7JLTqBk^n`mrB*@B~g{<4Qu5}soU@NJj+=5J&4nVSBWX+H~fGpiI&QDX5gcMb^wp^#JXxAJAqV0u!5rE9_#=`'
        'NJoM;7TE0;;~cR)2D?o{!E0PGrA2zHqL)M@Sz60qT4JJB$E9I=OU0DTWSE~@{Pa3Bad4x@h8?XtUsE_cagLIkqXH'
        'r-'
        '7~K#sUK4~H_4JmtC&o%EjJ6f{%i%)6nZs~r5Db4s=dH>nEZA!WnR|N&vD<)Obl!MshDTgXNo)X#ba1zji{Ur{Yz$'
        '<+yvD!_m|OlID~2vWfDb9MTyce*nXn%)I)-vCt1q1BKz?-'
        '6npww^b15by)Pt570*U?Wb}qdcS@b>D4uPdcXS8v25@<^N>0r2PThLd?Yt13)p4Te0&Et@s$cInO0r&U!`q4K7zi'
        'lNB>_rMdUEk)VgfkCljLX3qIAGxMeRfm3w^dbuaw9xNZf}x{7Q3q@^yi!xg@Q-'
        '?gvIP5fG(r~^wcj=hMpcFe<|8U3h#aKV}(HFe`AiH-D%tGDKrHdbwiljF^ol&;~z1iw!HxWg<wydogztu{f-'
        'S*<SGp*p$K^B_K~+y;45hjQy+$LMl++V=+%-'
        'w<S!EKz%J9qqcbj8s)PmKI37y35PP4}<d98X0uV=P;FD%{qLhOB^(83xL18P_)o6uYZL@}FOf~=-U|o2X8-'
        'h6SM?&imY^53eO+vPi4CrW3d9lkYcMdGSD%&_Gx+t-'
        'N=U_+Eju?}~fg}3r<TAhyVBK3j#L@we0ay>=wrUJt<purr_;b9182GYf&kNoyk2oH{RL@Z^=z+<2l|upfQ6A`oC8'
        'D-$+d?s`z8q{iNF%CkqUVlaz-`F6?Te~tbg0jLH>7<dYO8wV`h_C(t_J;e#@I5%X-'
        'j2wE17dpPFf#2PC(u{?&KD#kk1Z~-'
        '(ZE>%??+YEL3FNsnE0zg=f4_GPy<8auD4$=I2NmtU(a28EtQqDJm4Wyv5N)E+&&M{8qZgb`A*^RZcXm$H1-'
        'A*01ZhCIO}(y1WFtEvoc!G&d8+3>uDQM(%RvY`zK|Bqu;4M`@rkPU85Ns&Q!fe1e9Sy-'
        ';XrzLFqciN_bTZy0UnBN)1U?#E@9C7=5y#?7SHnpPxMzUJ|;kgcJAraNj-Is9sNV6EV3gTpgjqV)raJ`lS{@7^yr'
        '_NU82Ynb}{>N7lRQPJQ?BbS83&2IAJ<*-'
        'OtTa~XusBW1XsiHao6A30KEH*lL3gl~Bf7n{g&DhJZoAD>Wf8i8~L)MmSJK?IWl3^L_pq{0Vs8qOblQLGc^iAG4^'
        '!M;VV9kLap-'
        '<ZDo@jAYNkb_O(o1gX?BxhtX<G%lpOL84Nl&KQaR+hoS124pu7D2Ufpu`c_g<l+MZv0(iC47donBua708I1hwHoE'
        'd0htfi3dyz1Sa2F=mPF@bzh43==Kow$^iyjd+IX8Ps(2F;!Rk!ntF9uMYexHqbjSByuS`F-'
        'Y;CKYylRgRM5}p!o&gsGr{i02L-JgCTlzSo9y-RsR-DqjvzqJ&nydOtHD9-'
        'zE{7dWNrn%Ru%Zgn%*iMWVbIB3N?(m0s?)vJf(&C0#b007o2*ITHFqBOUdThP0mFl2Mt9wl*#@UPO-TxSgwbVhbm'
        ')WwA}&Rpa~8HOkjmD;XNkVLoTf8gz@0yZoC;18t`7tL;T7q${1&xf?9fYxlncrJ>@h|7bk4;0!UwjL8r@FK$b|BF'
        'T*A)+_~ZT&{pyE5jev-'
        '!VX^BuE9yB8`#cX1>Is23FRq&?Z|w^XOH}zbd80PeR%ohRWbLmJ5Dl}Ef>o;jOs);*5v**iAmqCPTrwE7)$Nu#-'
        'pydnW?>4Z?6pzys&AX@tV^#nKH<GEwG~Cb;ISf{Imxvt5GGcSF_D=Yiu^A4bE6gc>!6N3T0O3T4QK;YYTm)>0EEn'
        'Ehrj5PO@9oU3skoNE@chOxOSY_kXV6(lz-aeOJ|Z8{@lKU@#4p*&zO6`3K#@Su_YTi1gzHL4S(mbrXhYC%3tC`Hc'
        'LQm<tyKW(`p0rUy!^1ZUGznHDFX2F35{$*z86H;{A+QeT8rbn!-'
        '|Z|~iReal?!O`twt%VeEC=g8vC8Q$N8FtMt&T+Y}hk={6*=D2N9JOo6&-^=r`M2E_y%cu{YMpr%b4UlJqk>F)-'
        '9}Mz+k;#}=y1R3$6dYNp1}1?HY7EnYh=%ICkpd~ZMg@E7p(zxzcA&`_x(PHjXzq8)INg;M^bu(jnxZ+Q7T5OHta)'
        '@tuNbz|-AYdO{fAFflwi}QQ?7mV*jj(8;sBsvP(|LPd6FdRw%=TL6l}-J%o>-'
        'BXX%R`yI8*LvGb)jraBMCpwg|qD~oqRhYM-aQ3dcUo-dZmgEwh<e@WbdOWa+rU)Idp>iqo%$F<Xmw&}k2Y`o5Y=w'
        'MA^Sbwtm@)vK5(Q(F`gVEfP^+UkUib>$oDWlDvecG+lNP%GYJw~GzUwC8Lnv2>lcX#b%m$>g@$GuI#)q{s=rafch'
        'n;MH)!iq`wPbU(|DsD3I=ZydNcZB-FbL_S~klmNV>`qMHhyY)q$uSxUXjYXT{cUMSSAg#gtyP;FT4<x398qWyZWz'
        'T^kAg!IOf^po+ptKcu~(aW9>*8V+sAfdS`Xjk%U7BF{-'
        'Vim*30>Pm4AY<@io&A*?PS1`1Mu}EB2LdKMkJdZPCxcIxt`R^R%QRbUp7X4sEEW>u<Pxa;KObAgk{qCp8JkN|LY$'
        'q_Zt;7$$<zdkv3K(^0$E)?=46;aSm8d_87X9Kd1@dXLKEfeD_<7pRT}6-'
        'a0v0^_T3Fs}u;LsZipB)TKi6zx&4P)B$*qi2q<QbBF=2n)=c9p*J<|NRUpgT4_lYn6;hoP^i^#6&e%Zvb-mgeG8y'
        'p+X?HOR|(385^j#QJkShU~Va8Qg#CYRl@Wh4vlT+8j=2RU{LpwTf2Zv@ZHOa^jGhC$aw*GrBSWlMcP9>=Yr-'
        '`ZWRpCskPc%lU<5cSpAaOv7GRpvLvkq%b94fzC5NZiw>0;3gKrZ_SoCd@D(9VDypK0wro$IIJ&>Qcd*Wrt7yp&RM'
        'pi-LDdoQERN@g=E7Qh<6r%j0(7F52aDy)68u#=qulr}1pWtx@WPq'
    ),
    '_portable_underwriter_1c5a734b0715.reporting.inputs': (
        'c-'
        'oy>ZExea5&o`U!P6(H^%|R?cWvEhap`Vy4Z1HuHhVoF2n1Q89bWZTQF7LsroX*2LsAm;V(0E~z}n<+_;C2laAq9W'
        'b+7WWsaag)brr?6WKo{5U6hI>szs5rO;NFEyRG;(syVB8SyZ*iw@cS`9cNP&84JTrQ#Tb4Lnbnu1{HZx({ib0;v!'
        '9XOe4!^9UH+9QCWhr1^dkZ)9^gzN*cC~;xv+yOC#A1DTy+wA5yV4v)AxdP1Ji-XvWX;{erz0HLs%7ar9u`WaXYkl'
        'I5itD&f#D0RNYX<6Kw8I_25zzT_-0%kSJxr9kf81#>0e@k-'
        'S6dEHcb7#Fg3@13_r+GP2s>gOnJ0DZt@U9tbR=eygaMO5FzNM0^s&#H>{@TE+apFtg$us$oJO2{Jrl8bu09!_*%w'
        'e#Wpm+-^+)yMGS^77*CZTQp8)w}Te)78h@&!Fr3lT(uT{N?8I{Ov_}{>#<pZuaDd*Nzij-+cP}`-'
        '>0ZyNk>7FYj+*`d=3}D|1tK0B6DUAp-W~F!--'
        '$nH4)(zFw%&)<i3I+75QMLecLR&a>k<bg}G9p783iLUZ2`%`U2{sJxpduSLe`i@#D@T=ymtk|*r(f#)n@b=AoF5t'
        'cmcHAPuWBxGyO%Bo13m?w&|&W|mXJYdW>o(H#8!~HoBpGsnFyYV|A%M{FxZesib{Um-UL<~2M{!-'
        '+|Q`DZgv=(*BS9F~LbFV8ABTus;;VH=O1b=i%u2kd;fyf|kQ?X|~rSp;VMDVaI9(lD=*8+U_i2Dchj}j}&@ZT#Ya'
        '^w?G0LPM|0mWe|Hg&iba6U8rnx^BX+VR1Jnn?s4L981*v?Xw=1+rqtGoDYXt#}I7+5ss5Gt7(@!#9p$2$kCsf6>5'
        'N{|MJbQ3IB!48hi^h#@|W^i7IOuv!c3&!>M?uthGiCJSSprlAzyc&AETV8S;L>Pj$v2%>cudXlFbpS^lRmR1C5Zy'
        'G%prkC_(i6$#OzZDT1hU8S7Xh+FH$ZJN?L($(=>M|fWk~uH(S3E1ht1NA_SD!khU*v4YpO5TmX);^4UcO+)wHFN7'
        '-jT9{M2s{xsJJZB9Zy1wuZQ6WK|idJw<(?91sGzE9iUyR{ZO(7B(4h~feLVyI}t%NWuAp7IPs5J6=Ah;%|>;49F<'
        'vVf%+-RvS=34>5CwBS3sEX?!idxOrtw{3Ak2=9ah@wM-Inzx`)pwkh2ro>$HatV_zO+9Es;y+qo2j+=V?j3_`>CE'
        '((oS4x`Xez=}e{$x#>@3XH>0Pr|n?xkDQQ)wdi{p1Pu_upl$|mYfbS7*WXo(M~`cZ5hT>xQ`QSg^m(J!VzjDhevx'
        'YFfjS(dE*%faw$zIRA**a8}cLpHtrK*dTuW~$|)Rgfdj>c!ON2J2xgwN%4gRfp~W*HAIAnZX(fPq!wzIAF9JGJ-'
        '(jxd{Xviiwm1ZQ;^IfhC$gs(p&sj=hCQLb54n5nOng1^CicUJ?Ue&|bxRb*ELodweNp1vP_`$5EPqW_?2VmaLgCN'
        '()W~`x`?^OC-J13ruL=Y-!)8F?TFN_2m?j)FF$y^I&Wh8MzN#i#SEYT<*wFwzi=m?tr3X2sq&sfTYd;_d89-'
        '+pWkN^UFt==y8Pme}M!lE~?s)l;poOm#>HHDi&XQO4zRl^Tvy(2lqpZ3EgtZ5UayMu7184jz5)KMA^;W|1a8$p~u'
        'jqY-'
        'J)$O6mB8>Jw_jQz2brXDciL<^kGmVC1NY8gA;I^?yZOJp6uRLO4$@XaUnJi&X|Fi|DNKSzs@@ui8Kp(Ol`u+X`N!'
        '>t_iQ5|A8xCnqN&TK4zZkHsVbhHN{+b(B=b<&z5|Gt6~t#%A5guHq#Kl^eMx15s(6$kBv>ldry-'
        '05;UgE@hdQKbvCWIhNF1}r&#EcH6J-'
        'tRo9Mc5gWFEPg=pVI>8e+*>lzR4L3Kk0$LIvrAr#n=f(?(b;{vPercAk7yId~shec0=l}ZdnrX1-'
        'QNXeI)iLPz4k=%l%%T6#N)k!h6LBgU6cRa350G}|EN~`F3T`{|PqNZ|Mf(LZS9lI@+>A{u8X%L9_VhD(+_gmLQ1Y'
        '@Zn%BfKEPre`IL`oPvG=mZXu4~1fNauG||7|w8AnkBR-|h|1VHmJSlCT?~3Hoe6KI)s}fGiwQWK`;4NJ)9_!Jv-'
        '=_?fi#&UZYOgPVB;8hI{(b5Tl<aTe9_1NkNCbKCvVN`O?z4c57wwq8bQ>b-'
        'nR>?THF=^}@EL8(!;k$M{)oItf^3=k{>|N6#5RU1K#jqY`XH-'
        'A`IZZ^fAd0(@o@0GZWGH|HS_}!Go&iUG|9O%>Qjb{w{fXX`-'
        'Q;vtSR?n|5Tj=i7Y+p)y#evu~PE5$0cF3eeMEM1E7Y^LCOJakZgBF=KYO7UWwl-LZ1i_@0VwMLs^Yn~Qm81Sb9;!'
        '`jane>pDc#;9vLbBVVzFvaYlVOCOnO6`zHRz|4Ylr=IvC`Z*Pvs<&3pEqozMPGD0n^tCuvM}tGCs$C~TKtwmO8sU'
        'a7%;&}&f-H4K5Zk<is`)pn~0ZmNxiF8d?HPWbXysB1h4f;{ntx_#fDA!N@-7sf}4kto-'
        '9VCPWFsueqQiC~08bzMzHxCg6^-'
        'z)7SDzd=I)CX;M6&(((v%(1eT+sjC3$^ed0Ex9er~%qj+cR%q=Fs6S^;WO2Ee0M%{b1XoETo_*ip(QWd%|;QS7np'
        'Q?X<Rbi-'
        '2_}(GP&mx>dl`?P_}d)PPQgRbOP*&Po^ztUh#y(1CNN_sHH*zfLvF^l|SD*n4&s9J9A+<S7%#ag(e)ImRQq#b=1u'
        'LbIMI{4~l1@u!w&$F$h0=#hMTq2E*tbv+$RcqB5}f2~z}1HpM_tv}b3rhMyYd)REIf51>7`ACnN!gNZ-m5-'
        '30+%SZ+A`IQmzu*(B=I-+m2%BjP$Qm#!ufVKq-TfAXKW-'
        'K&SeKF%J7+WPA3!vDBgcTWQJGCbn%uJ|c_4_W+g&j0urnu6B<|$q*?iodW(zxxj;U>BbaRZpLuE+dZcNc%7ZorAR'
        'fXsM&!`1vHksGG6@zqXTqRSDvopW9q9v**-'
        '*T@@l}(<FS#4hb@F%~s4r##{W0ecNw`s8bu(p^1dA!n?tTu*frpk_ij7^0(n+<ZI7xXJf62q>WQVa!uEj9u|s{X+'
        'hqG6%(LOWxCBw<n|6b=(78j0FR9KtXa*I>NY41usmRjyryjV@R5q*(t7j%Ybpt6*H3wNtYN+R=U<9pbkaYh(7eSO'
        'yH&r+}1S$UO3Ti+l<kzYlCbIn@L;PZETYHcns<K_jlK{lIalIkCXcP)oIU1VA?t#zLqF`)I-'
        'afK$OGuuT8F!oSA6tQr17PEhfWIAHA1>peV+hHUKr5XpyVoq~}W{YeRE>nHhrq(0<GCes-Ifb6`?x!j3AuVMK6rJ'
        'y|9q-?fNfZNP&{7gU6i#)D-'
        'jzZR!e`8y?v!~HHdLCyL=#zD22cO6os3?~faYs7LyEqo{3IFOPRZ*%=TK6NGdhdf?*0q>;9cA#O-'
        'cWT#y+_TIdHoz{>iIFr&~v9=Wuk%lXKH^_umo1j?B*x?Ye6rp^oiYnc}jm)i3~<}(#g&><O2O~C#lllz~s`yEZa('
        '|2a`if_|E?UtRqg%'
    ),
    '_portable_underwriter_1c5a734b0715.reporting.evidence': (
        'c-qx{{d40;Zs_m+E4WJ4D>Bh2Gn;qGD`mCyW@o*L>*ni?XYW#RsaUi`+006$j-'
        '+PB=lFkrKz{=LLDJsYy~@?qj>YaqqtR#pjYgwqv)SwFx-HtfXLWh%+hU)TpQ>$HZ_1=Q9gq8}+$MdKbepCvx6igk'
        'UnFgLY}&r6Zx&}~FSo_9FWWAGrggV3`ZC#7eGgR+&9>Yp1ytM>o4!k`8o>0oWmhKE;c)7U>wTGgD)y%`X|DgPgew'
        '1f2E__`g8d~;y}yIM>h5$XyQFT~L$R;^T5jj?@ramdTo-4v+3f6W*EWYF&v&Q()RuV;9SK-PT{nHvR{-'
        'ejOno~P{jIFOY4&^Q9!nR+^+q>(Qyh;l#(8pC{^f*y$l6GO&A#Y5KuFazpXM<3au3+S81{v3QJ)UiNFi1GqVCHZp'
        'z}QWP!@YxrN28`aH`|?ZS&>sBNUh_@KM)!T>;S%2Gr^s7=alV^me>U3ZT|ee>xWR7CylLk6TS6EWjDaPxZEJKeq@'
        'kf3f*P@h|`MzptPF%ZooO>?~LH@zfji(z68q_vYn)<ZoVHyv@&l`sw`D$Nb+uT>O~7e|Pcr<K^5`xcvFUPcL7c=P'
        '&=`;?fjmXJ_YX)-KCKQTNp*S?K{?iMF#EChJp~ZyM;bF6(|KVa|@oPQ^aomdCOdAaqHw*_;k1<iBmcZ#Gb;-'
        '0fgib$NGN9CKhn=tNAlfe1s|HT$Z`i<_Iaya51Ev_8AARp0NM{*P6?^|0(tEwHvhVFPV%nzq8uZ_A=T6h~e33Dy@'
        '-5(WfVRhx<o3FfPWHaThS7O8*rXIxHAn|Ft%>2C$H=U?E{>!#~2VR8IWbX7-'
        'iowdzp==g+PCbQ3Fb#vS2u%Kq^vrAauZP|4&$V*rsC)P~S8XFb+J+BR%+ch<<eW>c{a605DGk~PL`g`~nhAdVfZL'
        '~SHFw4zB2n=X)Mw#Z-'
        '`Rmu0Q2X0I<p2EqxhMh#I{)zU)yIo>Z}SiD{!B{GKAiu*pD#X~|H$gRdiVP0H*c}pJ)f~<azFcmBfG=@2q83k7??'
        '(^zb|)!f-MrzZx)(j)6Ks8RPOyYp}Ch`4OZ9ufK_=7&Kd*VKb!>!mB0J&<N1dWwNj5-'
        '*&wyj7`3uNYNbJRvq5U5W7RFSQdMJ~MaUKHAISCU=MR56XGHts#oHf|w?Lr&wXD0cmy+>5yxJoxJ+R7MydFSg=C9'
        'BHbpHCc=sw!lj~6fh?d`kEj~B1VI+A^83dtW*(4xHF?u;x1W1+gP_EmqUKiw7`2;d#+a4LYilSb0W4h;kJa&hcHG'
        '6<!SU!K2t`4-R#4O;wnNOcUWk0~l-NR14r5-'
        'bu_rE~ZG^}CPJ2_(HS1v8>#MikA6vKde~L8W7c_3GvOmp@#*zW8`?&IfZplLkW}$ehd$MO7<`cKDl6QT#4Zi2>oe'
        'ZuS6hFE9S{JpbY4r3W>p&alz@5AS|>ef|b)jX$4%5OROEYo+;i2kZOA;yJYGfO%VF%w_WJ;`zhb+1dX!7F;TOT77'
        'I!Wp*Y$ftiNGc+~*DU;3pO`K~Pv<r2)P#gEYPC;TP8!w62rehIeM0!*&9E$+nUBd!KH(xo=<uDZURlZtCmQ;x?2u'
        '!ETfixyh<r{lhqZ5NA$Y=pdCv=wM%u;!{BsI$eY4h*LjRDc-'
        '}C0ciH%Kbj?z=W_x$F>0@@sOi|y0nVh5|z>u{=Po7HT2)10f6ndV4x!dfW7&-Y?sMy-xLyZv)jRZQY@4IPTs<jg;'
        '~RYMyEv^kv{>^<*e+B>k^0$#1TJ*^cFt>G7Jd*E4qh&ubXDCx*P51RdFn&B>TB8J{8p-'
        '&1Tu*#uO3SJelhy#adxn$x)1<_LF3b3)7>fi9}Br_yI0Gl>Ke9wS?-LQ@bgrbxEwcH)UU7UD;VD49I2T*_3Qlo(-'
        'wjhp`V?9cnm^qV@(zeJ&`?$)FYw8L!%QEE9JlB8uf~1?WcUB$>PJ#N5-'
        'G4i{U1Qb8^a54yF)E?F;d%G`3Lqw>w9j40X~1c)yTY?aQEa2cAiM=mw88RDd^g&5TI0PzBo#qomwtfvtD2%D_@7u'
        'aPjlfc&Nar1K1R@=PzQVs}P)G4@CPq*c+IPLpf>bJWU%IWM;v#YF@(R#WkVLJ^?o~V#-'
        'tKy~xL0WCPQP5wDbw)+5-e+<y*nnzmtLu|eaE{(Vg_2+6rgWM38&y{|-'
        'L%c=NR}$PfpSN%yYsy(4%Pn7{_a1Qpl`X((b8VbMAaS3RxS>&a1t#?MG^YGIFVeWt(sWI<#=GOsX}r1+ZTXS_?&7'
        'a2Vh{`Pl0H4+R|s4-'
        '&pdUh>ljZf(o3^W?<HoV>8tbwrr_av33}y#yalG{m$CTe{cU3KG57qNn4<~L3%#z_l>eLxzQ=hv*g+LA<h!|wWzu'
        'hDB1%LfxQM|xZIw%ZPQLRqduTT*C|WN!CTt4k|4_<na=z{LC=I(xdf^GwdvW|Xtz}>q&??w+Vy&_ObdZHnjXqgd*'
        'zG?Dhk>mhlb$DG0$eRR}$BxsJB8UH9%8|hjog7uKHU|i)UaSZ%-'
        'TQhekIvLd(JWtbp*i6BVOM)xT=d?UK6bld7xgPOSJ;_A}Sx&D^;~Pq3KLbf!=`oVq@_E|UUef@lLawVXMjmpgRZv'
        'w_Zl)uny}8C!y;wFKE$U4O-'
        '?f{Ww+K`zjyB`h(w#HeaTp9NUIhb|>pTLRdYDFwplAzI)}0yLLZ^dGjS8o&ZJ5K0O$$XDxZ0Th8PzFnfiTG8hRZV'
        '#cc1rSu^Lux3dLjoB7Gxhw*Rdwd>Y9sUt&a{Rt=Nb_L5$^(#8=Y>J4bxu1S`5yCnc0;d*Fy37!jpPjP^<#*Syd?='
        'Of~tFS5fG!HdGKu%6}Cm36bE@%n|}J&NOWa8onmZ9V%j@eMM-'
        '^sg{FvkEXY2mIH?ZoitRjdrI>|+1`|4o|g=iWx?49&4McsBmi6un(9g(C_j-'
        '@1;fJ(>PlV3(K_=%^$}B)Ae;ZB7KUYXl=WNK7HvSP@AtT8KJANEe3o7bH8y!v2vxvxoGRrXCj+Okwp=%`KJ()qO+'
        'nGCQ9o)`B{TVlk_pz<#CCQX>~{;ne#<<2leeZNwmtpo43Juyb84wkkE+uNElC55$F98v2d{cQvy2O3nc2Dq+5jf0'
        'YteG->~~85`^_1?J-!AYj6GAwE?l|7(N4<B{z=SCLi3e-e4Nr!vc%~~{YJEuG_r$Rk#SnNfR_A<5J-'
        'Hmv=KiEIBn3=Ci<IgrN5AdWXfn;^4T^g9~A_5b*gf)N5GW~`_dl0o2i|$j7o8Jyl<zCL?#4LwB;0=<R7A}r}316G'
        'cLQOs8lkFSiszriwQ(!sHoPC!TBfrD(#TntZo8fAw~-'
        '%_ZFjX+6N_d1k%Xs68_cmwK1P+SQI(6B2|?a%k`2e8S7!iTItiBtB$1wBhRZYKQ>2s;FC&Z=cL0-'
        '=m1`e;ms;@@IfkiHN+riz;C-'
        'fo(_NkZ%7g&EhWgk{Tqqyfw$^<10#`YFDiJ5@R6hl8fZigsaiy}xbwOQi7HQADL72cc#xP<;TTaVrg5S&+{emWW&'
        'z=*AQ8Fm!3oJfD+7h=L2;E5d$8Q)R}ROOiA*jsFh&kWAO+;4D~K38Di|Xmec8!5%dBxvBr?7mL&)P@G#|Z>xG1my'
        'MS%fLQS`w`0mm1y#Y#Y1kX6h8cmr0_UyfOe=1InP#Egx~Wp0GnO@kEqn%1P+T)UxH=vA9L&gNB`aob&5PNY4OG`K'
        '<>Lq4DctvF<Bkr@!0SZp3*wmmym1NA1TgeP`Od#ndkxdEfS@7pvejwzzpG!?BfVFTK2x%g;ZE(wrIha^^=;2d>4B'
        '9IT-&5!ows_n^GHKU-'
        '3fCZdv5gDLyr238rB7);x4*8l$_uAhSg`@PojO+wE8U2pAI4UQ2EPCmFow=W8nQ`aACTJ@U?`2m~*Wc7tf7+I_2X'
        '$!Ob*M5|w#BmqBLoC6^j4e>$a#t`s``MD;~|9f*1afj%VY+E646=wS5wt#2My48khL<k%8q3#L)rkjtMC}+PT0(v'
        'QBDqF-)ydy^W;kQEzKeMCoERmN3|oL+2Ge}`0IFQrR%mVkHYy&tYFc?Vu@Zqv8T)>kkl;?%-'
        'lj3>K&sRrQ9s(kP`;ZQX&Y@7Mlr73E1zF=ZojrqNwlE>@hQH;TmSHoBCOeu{tmjGe!}DB8<cKt`XuBXozp|QE>P?'
        '2S~z{POwpkM68CRsQRWa_IOZ(hg*bji|%yLsz7zr-'
        '4?Ao!sH(n1Q@0KLkPzDxcF<?HeI?e)jVdPXfQHlB|75N6EOyIyu?vKh9PV4p{Z6JL+QyFfMlE=-'
        'nSW31X012@;O^c5k-s~#A@Y?Y*7`x-'
        'qR4_t7hkL?C<QZ8OiqqGPvhOD~BXs356m0IUCW4_vZ;Glk<rC&O55{n=T{Dj=P>F9Hg*Khj*MZbKN$}VYK*pi8Qf'
        'D4=5pMhyIbtFXf%X<Pr$S6KWAx{~#4YXpS8@u)dV<Q<KJrMlexIz!?Dnr_}@>kfS`*m^3gkwpz2w!o<Oy4eqpeqJ'
        'w9O?i$v;`UAJo%DgLTbow@*(U}oK183x$m5Cr4?$w(nMYu!JZ*Bv$3yi$87b0@~HzT3`=+IDqCZN>dxfw>=Xcn3I'
        'A2|_J7_^=X6^1jN77C~&MpbY2sDD*xwSj`s!CwH|*_WB^gq4aQ5Ue5o2-N~y6_}N6@dQMbLD@-'
        '%!2T}5c!g${d_gCG?A;=+mWZ#`C9o?+y>*b#3zrNq1j_@fKs2*(N~NmP?^Z!WC_GRXl)Jch6{vrC9&&8DiWo%ltf'
        'gtURV{r;Vv;nmg=SHcVyZI}*tRt>^%!N3(K+}BY+T`wwa>YVMo+PWWm9bc8@tzC9%goomy+1Z@$fH?<2dcDV_8I^'
        'VE~k{nPi{Y*pj2@eF<8Oq%_P{UmS31F#PaB1674gIH+$Kvmcg06y?l&`v#{tjHkPp99(IzyYg?OMu~VG_yGlG9<G'
        '~Hz3ub_I7}dIXzZ^!qPqe*lWQTDH}?WkQ#J{XNm=AXrrYpKPJdFsWxV~)1p@&@+!InF;4h5_8h$9MG$l#pQ7NH2f'
        'dz#)CCoa)n_75<GXe1d0#dJ3d4wwZBICAp(-'
        'r7K<PTp3^1Y9m+LfMS?wnR)ab;9sfE!mzsfFCyF{{K_zy8OW<4IM6T&aIU7|7{gF*XUfhrJ^*W)Tf}ghMA~v~k1<'
        'Oqgdy{*Jgf?cDi>KV@4LVlM-}gy9|!Ha1qfaj-qsnWfxyfi5N*`E+R+y%zvyy$+(wg^X?22GG5GHS%G|2NCIB!>l'
        'lBLdYq%QyDUk=BIbL@+ti(aPj_V5WeV@-'
        '_CqWpA4kevzl<xyU%8>b{f*hg7X634a*TpILvfJ`4F>NuXipZxX2ThTd%7c|07aT-NMxMC$o!2h6R6VoAgUS>{{$'
        'K8rpW^7)0!%nBAg{fx+>sUon$~7Kh;&qa|ul8yIFB5lG(57=wAD<8T1zkmt}xklU4t+f=FM`2j0O9q$VhM_vQC1c'
        'H=Z%z5H1gr!4K)lBz!C-+F5wW^pAB`%Udv--FwIuQ+}<C_-'
        '2J7*cW!xm{L3j=<`L(%<$ZLTD;i}Ek2z%5(!O)ioeq?xe&<vtKrf<%2yFJWN&s_s+h7_j=wsZ0f4R|tHaEs&!n5d'
        '0t=GSKT<#rVLsM>;UBq~lZ#M7CDG(^zXYwUqYOxVdMlSXrz~H2^z4T$6G+a@{?1ukJxxHDITr9s^X+f7%)k+?5wt'
        '?B?#@+}`XFEX9N=)=It~$^bDKN^*~&AGlB}`sC2S@B0Cu53nr-'
        ')G*G~9RV}%xrT7i7j6OEcnU{?*nv8Z1gs%;q*z04O`RHQ(<i}vv$8FwN)%-'
        '_O8_XvWq*Pq7>Zi7N#ER*U}(297A|hObrqPrH>AcD+bzoB#&%+&P~D+W!;b+{8}=|DS(ve-T4%FuIi5%Xk<#UE^-'
        '}>GO)IzMn7)^gl;Fm#jTGomAi8^`L?5F6bz5wHDSPIhatH_m5`VEWMH46!e|ZtF<T(6saj$_pI1{2@qc`?w3@mOQ'
        'X$*igC|b~G$r1irZ0??Q#jdpZezes2ZQ@^jgWn$Q2gWmG^P4y-'
        't*is>?b5Q*vr3DQ4fEjfq6KQ2>JG)u{JPvV!ih~{L1trvUGUhAxs1yhJfkOg@W$j&LqG|P*}0ZDak!Cgr0XFvY;$'
        '8Y7QC!ZJ7_=nNg=InmtteOnAB$rMSXCXE9hCb6K~z>Y*M*f-P}=?15iIm&-#<g{S;rJ%X^g@BQ;ItiNzs2f-'
        'pFdn@MQzjw}}k6MGgA5lEt(gfOe4fdF<HzhOHMyA~;MtebilOcoY|U*`E&T(^!zj6^bc_hvaxUU2{^ug*Z1j@|kA'
        'd%my=2}i9WxpZ6_kS>iYhHW8^Mb&CsD8@_Wo^=lPO)SAow0}3o3<^M3Xn_zzP8O#D#~HU|HQG}zq`+|e=?{wW7^i'
        'sO#NOG9DD<jbsbo0o1<LZ25P`e3*9&xp^sqFx<(G8ZHhSkh7+791m9GWpieCa!#9Dbo8}ON$$zM5)J>X0YI8yzKC'
        'ro~NUR1N{{Tm0Sh*Xa{Ty?agw+(Uv9~~Y&i%#QeVCnxZw;F7WWI(ymd?xhD@SqLoWMNnidsU^CAx=2UT8B%*?&jO'
        '6CV|$^L2p(6xiLv>Jbf->fGJzaGKZVw$C=!M%OB?IKxX1DY=KTkL4|}WeQH<%wU!mAd-*R7Dv%Kc*49#pTs>c-'
        'nAg8vtS3@7VU)ebE6Kp1wK+4?t_NAm+Z@M@j|qu4<|DZ~=7WhpCNL@UEO2$mQ%;H9iLv6o37w4((USq=0oLlcKk*'
        'L89rMpsnfEq7m!CT8!MhF&Y>{FBw63X`&hWZc&|xmlMtSqzAoq|AagWCEv6g_C03A&q9t5(u9mud3D1z+{jF(;y-'
        '$&WTk-HdhkLiGW)QKcV0c7L=dW^0Vq%}Vf>(Q-'
        'L9IJ)M)e6c!M?ksoU?}&pyfNffGY1*8=HM!&HvLp@z}PZ&7F)PunGsgF0=>Ne6U8iMf$t{0Bj-'
        '>`fU!>PfeYVsI&OW-w<r(vY7|#>B71AHaS6l+5?@+b-}JW~jraphoDjd_i#XG=*)cP==tZ#(n(`1>dZukvpKN4F-'
        '`?>W!t1&c%Gn2Yg?+6_V8fS9dF-'
        'u^V5Bqd)D2|q9T7hMO&vWM*5Dg(_y#)E&R&e~5rpK|+cILviHVW~0Q%rK=y{wf&rqY7oUadJq3WjM#Om+uPdv8al'
        'n|+C2gMm3?u3y_fb)k0Q|^U4+K~mqO~4^1eb~rjp7FRxi96|q`$*-GHm&U<B<7-'
        '|nwzEf*PRA<(12=f^O+EB(5DfzoPVv^6FF%MMqMi6$0aDa^D>mj_{t!?cCNr6r)waYx(B12-'
        'A}m)<Kg*LuEJoBnKYVqm<%p#ZpAY2F8!dx1t@b&=#jcXhM7(h^-'
        'JA+t`*@NLMieYU<Mo2>XDSYg;k^b8z!BqrAhajhCvz~X6puWHcQV2*J>{CU{Ii}6pIN|rSoJLAlTww7VBH&E|Oj%'
        '>R*Lj_=IaRf&;cxAmlJy5%!(1-{?x?vg5AS*hWr=)Dl-'
        '8cls*JRUKRo?+PujXr{#{nVEQm=ewNb<|&e<+RaC;TcgI-'
        '5gD+{tTy5f=@re`y;kRd(x38_?FS20zb!tMi3}qk;m_SH;=K*!Rwh_mKOsSX!og(#?AOLvZ?Cjfq?s12>K9XRQ~y'
        'Tsa=k%#HU>I;#P0bYaH<~|@ZauKKOm}}cB&r$<elnwU+-'
        'AI^Un3VM;z==or14>us<ToN2KVeVQE=gnGEt8ML_YV(F+w>&=d&Gpf)Y^wc+U#`RnhhOt_~)-'
        '9wtf?&THd#tKD^M(nc8|KW`N4;<@hNP|Mr{XI;=*9jgR+{xGjRFc@3?q!BTW9MH(p-'
        'Z=}b%l^b%JWdC(X)nO_sdXRgX2dC+|!KugP4IB@xKhq727%NgT$LuV)=`usC!{&k%MlqDbW?C`DkxCvEaj;h0fy^'
        '#-6B=DCCj&;}O3Nk3PQBCa~nmAcIVInYG1dsBB_f(_BW5I!-'
        'RvC^yB6dn|vLWuYr50lf#^jl<#x%r#92_CL{E78nIc?&sr|f`aHFYwMt&0I5t2F6mBiqJzQ{d)LH?+Pj)Djc<_NY'
        '7x2>oo~vgDk`EUFq5u8_2F)2y%Dnd@9i1X9`@MQ=gw?<rY!4-'
        'gTjE7Xa@HVDfPM1ErP(*6rzwaP8CJbZ=|Ee(l}Q8&Z})EAbXtD+E!fwDqZDk4tn0`E?Md%cFRdXbg!T2Ylm6rUKD'
        'Tft5oyvccUeKz(Tx|SH$h2E5V<)+crNG=IN4wD=^GKIX%d5=>E$*xiiscbD@q5IwQAXG$P?!Fx<Y@b(d~T%77Qis'
        'o`oFjg8~z!X*~CKr%VkO`wMfS5}Z_eY1zAGCS=5Sv&^;2(o*JZ*`^eg2tjenzT2mMbb_`VEK$e%79;k6~D(vn38|'
        's{bo-bpN4A&cwOS#4|Vcf@WTuDS`NWu75ci^?5kt?9AAk7EHh`V4GLeBWW<rCqVV+1DO>`6sS|HCF6Kgu!|D~8XC'
        'ffsu?mkBac>~Gm<8Uq5)uiP@s->Rs6C<hXRYjg1svD<UxAMDG#%wVY$%2EKbt4&;~o15HY1phat#I~Yb0`0o$5p-'
        '>!hvCkc^#vQI&5zoM#0mPG~TG(J}uyWX0V);C1BO$?L^RALXFbN7nQKnqM;n@7ze8Dg;hqX!NCX920$%@Dax|{I1'
        'k6;!ilXal%r^JU8)Y7Mb6MAhiz6w;QlZ-8dob7K&VTk7+`6#@J{<XBA~;C_?sep6}ra3he=8lxO7Nh(A-wpQwx-A'
        '_dogOUAe%;O+DR&0Ooir>wCP0-'
        'L&E9y&@U;ml%_;pC%xihbeZ$TDdRm>X;#!KT1LoSplmd<3+a9)Pen;+2Hikxe}x8W}7BJz{ydJm|fF8h-'
        'zjzJ2;=)>K}%foQb=7e@0})1Z)PY-&jYJ(fl7rgsUhoWNJt3yt8E6WWS1ZO;(KQRc(I-'
        'H0)l=+mQFWeWz9bzmK%q5V8Re_ucC@PlvX>8T<0C}3Cl__gp*Sf`}Bcy@I<fEO+RbKTpFE+sgL+u!grOa2$@3cri'
        'r8NC+HQX6Blxol*QJ!~EXhsJBn!q<vv>r!zwL!NNR*ea1sS%P=3nKKW)zO_Hr*<23Wy_$x1ELR%#m4DkC#Fvdx^&'
        'V@b>%iSo2viV0p;qi7ig&rfG#+k|4X!wP;pcC%<mT=Lthw05Aau1F&6OqVdOmKo@6tKEHyKZ7@&Jb2W%w%Vfq|0i'
        ';8Q3I0)7=)5Cr!6Az<UTlf$vO2=t@!%KQ#y9eBv5FgfWY!q28XW27gtH)lTUh0$C{E&%ciXt--'
        'Io$Bd}Mpn5&8s25D=>07znd@JKqfCz&_XcVXQ}swS2!f*9lr_-qMhh8n0c$1_%3}-'
        'TuV9yJ^#vK(iAC|YEVk)CXJ#KA2>Y3KThF=y29tw~ht`_~MBZb@4Ie%(hYJq*Te%9im_n?t__2{(sXDq97prr8)E'
        '1v}wJWb9QTv7*R&VOek@SWU^p_fF=$Du&aKUt;nj-'
        'X+LykZ=RuPaPnl2#VZ3t9b!S<arwRBkAV6?Kxc)~6$@fL30H>da;1M%+hhfo6qSeiRW#-'
        'b=Y8E%9rR1eqH&8azciT?=6On_`lnhGj<I%SA)B?z&$1iIss+36?S2*GRy7A3@GO$^*ewa&O@A-'
        '?&tTrGs~eEP}Ge126AZ`0s?8>I`VRb5@Ageg>@ern9@IhmwvnIwOg><+Njx?iee0HP2h=A{6V16bCWC#kfW>*GS$'
        '|Czj^;>Q3h^I@h+X7elnRr!+;QWj{7-'
        ')D1rA1~M(eQ`H!5d?wy=0*guU=|+<X#muRG7P3IMRGQo#b*=>#?J?UAh+=0=puWOCtKwCUrxmyjm12l3qCg;2JUl'
        'e9qMZ9kWD01s}i0x;9}e)^25@9&qPilV|*@)O%8emiYB19W&$BZ&}U_|xQP2-'
        '>m*M|ppmRhLq^B1NEKzkD$TxrTFxj3Om1`W`yKovqbqZ_%esRxMBPBDnMc0=JlQ0-'
        'YCQ;M{Bh=J6cK;u?{R@dkInNQc>-'
        'J6B<!_mu~LKMA%+jK!Y}2W_xMie&7Gml@B#)O*jQqC_FT|#LY;9cI`M4r{5p}OFK&{Tc-'
        '|L17=!`#4UF;;p;Uez_5h}CZ<Z728lnLt;dD+kvk@b<mzkKkLE~L6rd`ba@8mw1JLG|NA+PTSyP=7L?J34G_Gnk|'
        'y<GfXkom*!-r2XBR?f41!Rj)5=}O-'
        'h!zXi9JkFskVQS^BF)<$0fyeOtU*3I4KXq}KaN(4>O0=c)?KEFHlcz(SCq|daIsW|`{&e4t8hkS&*2?-'
        'E?Q3>V$i7S8HTAk0OvYuq)#AcyKg*0-'
        'X{+m#eF#<^sC+8%;FI96U{%>$kGzOqRAfaa7){$W0O7<fN>8@Lx}hS5gHsnvNhp^EfmTL-'
        'U3B)MaDI95pXd1xFE7t8C!#@MX!3%c1a{o1?lCGs8yBa8c2?;d1(9^;1U8;&Y^yRCO*oNRkvWR)j%BMeosWaJ^*L'
        '<&ogOF}*zP8n6v-'
        '&_iIgMlB5~xq;!y2f)k`4Aa*n+GHgj)pVVRSEL$_Ac<qmea9=(N<o>8e~*l)#`!x_CbE}3H$WSKbuXDnp#hW9EmW'
        'VfEX^mr+I!)VjArSvJqfRid5E-45+ixh*Va}s&qC=59ZD>WJR0zT#Mm7F5$eKef2B0M~rFo-gVO&R3hf{OBra={5'
        '~mU3$~q8gm*B;}VQNK(*ZhO=#M+S#s^&j;VlmUuU!>N-54wB=p-'
        '350Pkif@X;p`eA=z^;IE*JG(7o+^L1(h~95HlPg;Iqn%v%%DVNu_?N8*X*~c5X%mtQ=>X|{z^>l<-'
        'aOJPgQHe?p1K;eF!`DqOJ`A4%8HPU&!d0_fCjfrEGOx3JiezP8EHZe7hJ8zc#>=nEdsQp<f8W_^o$OfHQ&71n)n*'
        '`{DKZoBaK|Kc9cN9G)&SCMJXN2WY?BMb&KpzcN)qjrWyJpU2>=Jd9AFL}yHL&pTb-u&MMcF}XO!f5{8lTHyW!-'
        '`8YYOTSZ}AKgBRogf3iH-Oj|Dtp=Iz?N+%I-'
        '!upHfaJR500VD)xOPrzX<&_g?^5R;xpzgqY$VR)}dz>Dt(%2PlM|`HuC#aUQF#dRF1zXq>z1+J%0xqq@oo9d|%up'
        'LDV=aM%<2py;UD`mImvp)gq0f)b~{e_F&<(R?ZkDz~FXPZ`>$Hu)J#moL0Z~2dK-'
        '0qNa=!^<cEU$>FapllD&kK~@-^2)T*s?0WJSg9b4nBd)IM=D)>Pyu@%5aV)_W0~-'
        '`2iUI}{(O^{$I`tD*vPtIWli=iTg_+aHP$TR(Vji^tUs*&3P4PzQ7qux`LtZ4PJ`eBo#}*{%flH_$G+$JqJmL>_n'
        '_bhZm+xQxaPj)$<Hh;d^(%%30p-0<5?(uJPjGk;XNNNY-%+7F9n4pTZRB^n-Af!X@}v7qQ5JsGC%RmX-KhWz%<wc'
        'AHV8f1gM;svTjP>)Q|JYG##Z6C!2KuL$MfDfEgqanHJzyZ<{Oaz@PptL$V1?yGaojp{Y9cP)jG`vB$hsW)dGt(jO'
        'GkyhnkbqJIz?L@gz@p?2>R#iD+rCk`>rRLVwu>It^SPR6Y~m^~0SiB1DpYn9(Dvf#&+yYQ{gP=FM)`l{%X<HTYG5'
        'w&dk&x{)qqUDAd8F#9!cswnrBa!}z0NzhznYn5YQpHqu5GqA9_EHc%z3A2{SF$UdSazb4%mqKd#y?;I-'
        '12_8xSr+xSI*0@%nh26wlm<9(AT#V^PuDW?RW=oWi$igB-aHAf;OrPQfxgcGBfM9GKCeVUmdK8--y=p8y9Zi&2!T'
        'pd@FmsB633WqnWdkfeu*PWa(-c3(@+}%(?6tQ59|?8hKC4D|9l6h&|Ois0a;D<<191NJ*M-'
        '06du9KF`=un2GiWhbiVwo!UIB4)eX)ReY!zxA60<PU<TvxbIkS$W+&Qb+VjgIc1B-'
        '^8B@$d0afH)(5`I`ya(>G$2dNBn3?CgHzkj!ww^PzL`~%M_?mS?3dEV8V1h}N-'
        '6)!vj&@sG4ym<}nR)&xuhDlCm2<Q=Ukpdc;stO9>2l`e^ba*d3Wcv~1jyvIpF}6W)l@>o`wJ<ofY;DGCTYE{bK+v'
        '1Q=j6)G<i>;dz%^K>f?toy73kaaGV%((i1Ki858crxGPaTC#`a7P4Y8N87s#s?AE0~XOHpV8V}8Yqjtzi8$mMeqI'
        'EYP!N-'
        '!uqi^kogq&6fLNAzZwm&S5>^Gb=7Z@`XTn#Z`qx`YF)0#nFtQ2rm7TbFZ6n*bD7E@lpS41(f7IsHU;xUJ|WOj$ix'
        '3G_SMT)hwD4O?#2GjGpslJ?R#^(I@{LRa^A1_`_N}D_BO;!6+ksrYtxELM5i-'
        'w)NfBo*Gn|yWTaR?j8G7V+!NsiGJ{vFA9>;!j?B|0X%ZSB_9PXM>oF=fh6R)FO&`)+0)q7c8ox4$PRKSs?VJd?!k'
        'L+c4;S##=>fB*RAb<!6%-2mC#yWcUg`2nK8U&d&Px1W|)jzeyX2ZvxIVs-9;?zHduzM4lO%Nlmy_?Ve-'
        'c6WRz3a}W9_5bpn%%jG_!pEZn3xwVdN0TQo8zs*MKRS)(<ppV`i{`%_K@}H@J-'
        'a#=k)31<d_5z3bS80;K0!hXI{OEwPF>=*X(sgByTh}GN2DV!MVPJPgtsEHr_2^#5^}8#Bz3f*)_<cJ(4?nX2*&8{'
        'TsC64-'
        'mYBtxon&<7qupfye_m3Um~GleexoSY&Lv>gd5p|i(kyca^$u};7N<f6^O^Nh&lWvr;n5m_!(uGABUDXJBtiytVoR'
        '5IK^0OBMDyg^0p{nZ2-RFiL?I?UTHV<'
    ),
    '_portable_underwriter_1c5a734b0715.reporting._underwriter_movement': (
        'c-qYx+iv5y_1#~=HBdmxDxM_3JghNZbb$7;MNt%eF${sRX-'
        '61|(o#~!+G+lM&*7aE?Qyy&w!vU5ljnZpIh2>n<v&FAO83)!Pmhey(@C%s9T?fSO-'
        'Du5x4b9qku>dr)ua>bQ0<4R<*@L|8pem!a=BbAj-qWySsuq>6s#;s)pV^G2<5yTD8l!Pg<fmu@S@=NZCx`-'
        'tzXgSy+QgL?YfGe6ihWRF|=*no869yW;8S<$S@(e+5gNZ%ZiUpHxb$s-'
        'Ypi313Qv(s91@bmS0(QdKuWEe6Dz(EeQO*(t2e58lYGFK!u=FA=ee?eEm*+a7kiKDn1m8oZSEH0j?zknCNrgS0_$'
        'DHPN1{1}$tPAis>14^_<w(ji}~;iVl1(sy+=45%3cfLco@&5bliUi~t%0=T|1(KE6^u4*w;pal^O+`&r?viX-'
        '7S?(cg8z@xZy>CZ8WE#5A^7R|_S&*jUHRGq@Wdk3XB9SY4O?Bv6&|i_-k4--|S-'
        '=GBLLOEh$z8}>VpC}wFoeWD)@>^?WmEvSq(6k1D`b)9E82tq8Av_k31a)Y>N2xbkcUEh3#55e@MRI9Xd61Di&j({'
        '7JaKBb|%*9_EgsFmDMW765$0Q<cE(8o?+~2w)KJB^G?MR5Iz}k;aOA8_1;$|U<=GhhfG1Pz;&5+)!223eR?+g)lp'
        '{Xs_OT3+p|p4D-;@->bWn6w%$Cl`^TqTN#nTQZ_vkfQL*~bEwaOj^;&Guxug4-'
        'zV^<K#yj$xMCch6`<EWlnjJDpX#2Rnf7}(?8U^XA1KTVG2FFri@1Z^k!;zi4Od}#5@Gw+%IRw|!>LKtda`uC(Fw~'
        '59Z2>Xq``;B2s0YvVxq@7u*2*cmh{$JU;Z_`^&j6Q-'
        '6WYM0_?L<wHp_mX&o$FpOK6ZwfdHC%*vj=?0AdS(dhkKIwy$K7h26|0b%^P*I$r+}t*CVM4XgqXD1&vG=rYd`h2v'
        'gC>Ohpn_TRTcuv(r7$^|t$CJZgo_D}i6*`NG}{JrH&xnY2_thT8Wlp)KvY#8Mc4EeL%0-'
        'Hz*xfACCwA>59C2cr@2MXYl+P&lF5i}r*#J$JHk$Hu4o$@`KGsZlFa2Al3mS3Kd`xX+OKoN}t<1LgVI<y$ovfT8)'
        'Kv0L$-'
        '9^08^~s|J^?mga)~JtOjnZ+4{+!35mEY6cN)YM*pB_^ikG6Fx_pGjUOL5l4J&wBR!n$Bb2zF3*zU3OS+l!0CDdAW'
        'fAXN^j+N2wqb16Fj-N`61;}y`lYQ{$DSoYPg%<p^D(N$Odu*EiU+YbU86wD%N<sDRO^|03U8Hh-kAPmmt#MexrKr'
        '1Wxprh<Dw4e@F*{=QCN4<<=;I}W1R_<sgdm$hHayt~$vra5c#qep`c=U+dwU7x0prPepQjFDZ9y|T_^LNDFApovY'
        'evmO2G*y-a9w==+HoSzRYyTw+ES-$nJa+=nbJcGie3lw+<Vg=2S+;8^5xZ-ylLm9KaH-Pc1hFR90v(XI>LBf*wSl'
        '&w_m5ksQ*!SJ1<+~^1XTY^2j22unP@W%>7au3ZT;#KQUZDbytU+Z`5X_8fH?x9X3k_u9H_Gq+NVVFTky1|(ECL)2'
        'MGHX8Ye!oxu7=et&UMr`7%R6zQo0@yO?rTi}K_~lIZ&t%yEn#vOt?}!8bYgotLsay67e!KA4)7W0zaZai$s0pT38'
        'JVWP3{(N`n^9i<myhMrE~C>!{Yx(r?dE&CVf0p<wi5WS4=9PMr!d^(AWm{Ki`oGND)+o6;K+sQPd9~u{Ad9&Ywju'
        '#`RNMuQ964Osej{8ARko3%SOCh_9>&53C$Fba1--0hYdvoy@CaPCPq!{;DdA-q~<@H45B}{kW772y5cNU-'
        'ykSfoRf_jkqW+HtHxdLft3L@4*iTjrOm{SsSx`uf!8`=TdH#t9Gk{s9>^GIUIZ-ttW5R>t-'
        'Vc>k2|Fx|7o9={u7nupj=+^h>%u}K{GyHE&q;p&Z>IE}RO3#4CJLy=@PqX%R8<pfHn+3W%G`1$Of$p8Z?ga6U1dA'
        'V=dIkZ9hjkCC2jn+;4h>*K+8?C2Y3XJ>uki@UBC7R_GN|3(EnLgA#{+fy?d}dq7OHs5=-'
        'Gxr3W*|%^c3x381CNYlJ5K(;I&_hr`OelVFA2~3)Qf&nUr5fpAbD=5H0?cn<h#ZosL!l{+qxD`gHq4Cz9Z5^}FMT'
        'D{`N?xhiw^6O?}e2Vc4YcBPz{4qtKKsE=81{T+JVNpp=LQYp{2b(KeWAhN!j!&2iArT`%lDv2Q@u~5(M1VZ_fbL-'
        'r6MHsk_T`@;U!NxO2lAa3*x2=t{@h#<cCx3T}cW2?UnXUL!gwt4_b_H<<eCh5I<9l5%a;`^=A?ht%rs~H}f~<nnU'
        'R7V-'
        '?N%jE$`8@b|JJcet+`9%^>;cmu#im9nKSiz+8>Gj%Ok1Vl4ocHN3`(^<tP0T1{SlZT{OeYJ$W?O%r{P&`q*%@#S$'
        'YOPM>hvSf0z8KC>E|c`SjM>_~FgoZx9BP{!=B2#XHhweQ0IbveD8+H{4QG#ED1t`LO)vzFLR4`ID>cyI1;DczDXi'
        '8}0I=YsoVr9=36SX|J{kF;AAi&HkO83aN@#WdH=o;6rCyt&1@3kRetcjW$`ev4%7lNcH`h%-'
        'q7CN<GTV9N$1rM$Fx(=mazr6-'
        'd@fz;uf75^_vyxWAqzlYVw>k@W9J^Z2K{d8SCKa4c>68=3tbbB1n{W7wRtJBYT@$|U!%ZqEhFHhwmPkirxK$cIkJ'
        'X@X@RNT%AqH3J(qxK?4>7I7pYobdtLRwIrHE+6+^-'
        '{w8P$6t<9RReK`WFYPcl6%2{y(&`sV8i2y$SuF>WqMjA|`+mY>&Sx(7)J#h8}+b;YM;}4}h-'
        '@Xn#AN!$if~fmA&RI^Y`@{T9AZ@20W%&$pi2ww8PP)$J$p<jthC>KXYrmes!s(TZ%Tp_;KD$TK69BW-qK0)J#e2d'
        'Ik_cAl2@Wsi4f9LhF7{E7V$fO^OI9cU@J4?cqdWmF5DUsGw0X0_8-'
        'C9lkAxiqJGe36T3(#xpH%(QU8ch4J{T@jXfW#S>F@5~qRO|EV*_@QdZ4;%7`YKLT3kmeo3%@|2;Tr-'
        '4LhVnx?H>_P6I_zKYmo2Xls;%gqx6#M=O1M9QQ3sYqGUO{-'
        '*O>}8(49{)0Qn>@*Yg|1l)~T*G=*kHv2*Uyoj_>!wU>fkmB3q}H+!AWX~WFD4Yo;Mp;-Zorq4X#yx&s=-'
        'ZXFbXCa`?<nV5GSJD<o@6MBaL(zW_Z^|;#N4oYc1Lm=h9ErJmJn}QoyjP-'
        '|eC7LVi|FVcN7DFntcUeYMHZclWS|3kv;LLsuV&&r?+!E-16~doB>%^2HgpT}6u#pD;kF^M-'
        '8LeIawRTnW)_IZ6ltiKcp5C(9E8Oq+zZCmaO>t-Zgz>T?6dd{j(_)V'
    ),
    '_portable_underwriter_1c5a734b0715.reporting._underwriter_html': (
        'c-rl~+jbjCk|6l5uZWDw$^t3@2&6=%M2S-CmYM3JE-R_BDx1Xv27v$>DG-5<07xR)IH#ZX?7q&-IsFB@A22WT-'
        't)d6QD3rV<~Q?81On8hvuC$2DI(n6+}zyU+}zyEJdWdc>15m;=F@qSP18~I<NKHUQF)q9Ceb)AqWNhWEvBQixG1u'
        'DT0})U%Zqt0j^i6Q#zlS>4F==Id{Lx>L6n_gS(Hqt`8=6t`Lw)oLw-A*pH0-'
        '?zm)k@v>oP?NjjvOz2tbP0K80Qvut`I>WmlD;XKbLr7E2ii@`7%o~ELFzQnq!@bPph@#+m2+JkbwoTM7W+vjgyzk'
        'NS=^7!5J!P9r|Zrr%>4;pIgEV(SRU(>y<_Ki_Gjs~+yKA$WHzm%<Z)O{G0^J4c#1pfmhc$>n=r$nP{TFw&~%_w?9'
        '^`l}joo8ohl$OI}2A`3b*>nOlj?%N^bTk62iHrz~Fcuy4^6{8zNnB6TxkTX?ASYHXM6bM{)$YN>Op;;RiXYr8heb'
        'A<$DJsC@VCFIUu_sAj;BbGEEaKaa$2)wImwgJuA=?{477vvJoJYB9Py8mlanGnN#?2KiD;C}6PWyw{N2qjke`6QF'
        'zzUa5fN*R^5NnvozC^x)9ElDLB%~{jNWK*HY*i29Vji4xsr02WqaQzlQQi@WjafWWS$r0UMue4ICtZA+X2?1-'
        '|U;A&^OrRZ+~0#``dTowywuWs4LtW1}i)?71CgZzb&@=+jnIx`m?guJyYwRtR?<C&*qa9MuOAR6KvFiX;8E|h|kh'
        '_f<%uG4`QkuAGSNuKQHomy7#_Vq;1YFh8}}wub=+;<?~nX4I+bqToUhJyx)I57ywEHFod+OtCkN{cfN%izS)2Me*'
        'fpeKZ+)NWz}}{=JC(_uOC07MshM0oo?LFqX9}4z*7&t0uBSAkP_V<-gtojM3ZECvKOb*7(b-'
        'R=pnR!fb@%or%6$!^SyX6A9wG@reK<!rF-'
        '#tmR=w?#}SH1;M=|UA{)(5_eSY?HcY$pqXQhC&9h|Eg;|<_=n!Ctgb!WXKDa5qV+|5Z4{roWilsMYv8jlIzWK-Kt'
        'yo~?EFEU!YzU}<tSB=Sq_EJUc|MEsF^MH>Db9-'
        'Q3@V+cWiR^U%^Ql^1d0Uym7Il>A{%w*=^0GKJnbe$nv}ayJWr0xIEsl5mp~ArO?*GtrpPa#NwS#d;y-8E6y$2F--'
        '))yMO(C4Sr|yLHV)YJZX}CTPXMcXnr0`b^WErne|D+9&k_=<yU}@4w7NhY;G*tUJL+2>wu8NkwWj(8RK>*ZVrQ+}'
        '*h?q6b@%+Dtvbuk(_%cyFLtBTY&1%z>N{*{d7)51taXbqjG~J>%WkxF%V15PFXV9U^!w^Nw(Xi;V0yAynU$*e;uJ'
        ');7}9Pu%`b{%#>e$LHLtJ{FG@2oAe|i8_BJEkSyG%p(Ig$u#jFK~bGDen%CitmCfUh!H!2YQ5M7Z)%Fvu*!F?aAe'
        'rS^W4rFXgkTu{@Rs!EGkrLB%L$Fb#K5X^-zpv`5mke>`L|3LS9L;@ayt8DQPJ-'
        '>$EtA?6Lf|g);)CGfPYf8<tK+2bsX3mcmrbd8>n`JIXxBxS+>H!lMiDVf7x?xJa2tXwO$#kOu<jjiEq9Oe`8+?{j'
        'WqBu=9A<&o%r|*eXGldu>lTMOF4`}nW8ES{J{vdwS#M{qCpQT!3qvFyT_Ux2>EizIS;u!`bsE>$#h=PL-'
        '(Y}7qdoG2~F<DPNKwVo}Zjd((dsBCUSa^6j{=p6=_+fqrG?zN=kgFF+9!-P)fTN-'
        'H#`r$EXgDli>#()O5s)yJbE$Vz#Pv#aar9#(HUCum9lc0~{7-'
        '({k5Yd+O({ZQ4%+ig0j%Z5)(Y(R;gXQFDt4X^Zlp2&VJlX=rSyR!I~-%jkq`QDeD7W1-'
        '>kjf1eSShc8fxhlt6@p6YzqEcX^A_Oc3=ZIh@jR)6Ia8e%{x>~&&sSu)-'
        'qY6QWW7qjfCs@$?rR)m*nf~#Ics$96AMSq=)YQs^%CpO;%qQ7MtuOlCwySlEWRxvRwFbqn?%Akj8N(TG42v;HWW7'
        'N27(=Ls^|2~Qy%J<E?bWnngKYKM*R)-'
        'nfxfitjte*;NXc#15rahQK`CUTd~pnNaFUJZe)o0!8C<3)oPhxFzt*DLSO;H2IK;LKdOsju4vTz)^=dvEUD{$b_*'
        '_4ad|;w;+S6bkK~5|Qt2M}K?H)hcd+c|2_}09x>HJg=TphF!g>3j?sZjhCSY$+#q7~$P#^_MV^ziR79<>{DES|$)'
        'FiJ%#<VncaG^Y8SpJ`CV2ZZ2%?^Y-|wt~+OEL)}pDGz$;dbfkeDIz7R4YdrTCcArSPxmJfH|1G-'
        '4Px#LcN$h48G&Da23rrR*qtOL?A52)WJG|~kd)fnzi;hqL)Fq@Y+K6X(vrrCfPTjpo4^btPQGx?eZjeJfQlw#ZKa'
        'W6-`!{jCi#wG-rt$ESR;No=ZGSYr<PSBM6&$v?hfzm+#A;|#&v>+mrL@RE}IOeser15vb)>8NRK~c^RC9m(@C}i%'
        'G0(zubcMKofja|9OZq}HTxaYF*Xs9n<IO=I6Dprqg!`;HD}uyLj`j*8;j(#kH>!Z6nPtk1c$x@jB+Q@jB*Bb(7Y}'
        'c#a?-u%u-n4&~TREHU=A5hKIIpdJfe}X);l3Tb(Iku+VS0Msr3Te<xsogT09FGCpijO*T==-'
        'SZU4FgkSL@mim%?wNzg?Ypza2Yxnd{ubq9J|&%RjS;Y7=lnR69>>C7dPa{jeN~}$y=A(6&1K4Q9%oE`hg84t>An)'
        ')c><*x;O2TvBm3nz&vC6-'
        'nv`a96cfbi*HxxuUu9ZkY1yS)Kh+6R%Qk1ii9i34YV&RHmQ#Suhse=H!a(6KIqH9`)b5_-'
        'g42KKbmn5R)!V5AhepapGEuNCsKTNqfjJ)o$N3BoX|Oi3If#mWZ|jz6YDqBQbx_ckWM+1n+^%SnUV>7;C{Pn3Gop'
        'p2oJMZ~RpYaCUSz{A3M~BtrA@72b{hngl3T(UgnC2U(;h0JEABVyj<D1v)8)l!TBK{y>yFaNJaJC1Tl^4_%x2w0T'
        '+Zv|Abxjkb1OUHZ8s4?4OhwbrxTng^d;)EBAaTnkaKS!>;J=9I?9r$Wu07ae}`L*8gjsl*vtf|`Usjg!svLHRGi>'
        'D+vgXmqL00r*E`#N2YY_$r-iYwS2*U3Rn?H4YZ2aThwH8uT10-'
        '0$Un@I6KpGH{PAtPrXA5m_kDd{y?1tIkifg#4s1@NrG}w(T(0a#_L%fn!$ap;nW4_jtmv}VN^gPKi;?y~3rq1DkH'
        '`KL+4jaNb6n6MXDuWy`0c?2Fs`t?G#jo_3HtogB@87QVN;HZ9xe(8P!K!(w-'
        'go~ha~d$w&U=TzI0l9tpQpsU%}Go+Mt=W@IjeQ(`k6+uWwx;HfUDEt?dg?ml5ix##?mwpIuNwS_kOwA+f>5bJ*@w'
        't<O%Qg<E|g!kAZD6Uv&^;vvT17?W86M-'
        'lAyzTXF0G=uCJUMhUoy4OED3oi?0^D>{<a<;iW`;|Ux1I(o<r<<@*RtQ%$BnQfN)*e)i58dN*oEIR*aP)3jGA7$W'
        's0ieLHiBl!c@F!BT?2o0ZRpA5B3YKfDzcNB8dhI*GYIF-bT5{M?)b1%S!JA^fZ`PM*={l|mklP*RUbBBzP%V5lY0'
        'us%%NnJFbz>XT(^?>d*W}h?uk7v%n(g*sIRIeh3UPE4o+#o`sAx+o1Kl-Jp$T<?e8_G<|z7QQO>jRQW+U{BOz9f)'
        'A>c3vUMSDFz;}<($U1b)@Nr<Rkr4YTB}D|n&dsxNj0^)XGt~<$v%Ef9=2jT)H+Ve6pvdj9r{hspaaVEgdtL;Mc26'
        '+*@|?Z6M2m)U879bQm+)Uk>TAGyIU4JTFy{A{cEE|9(-'
        '59R>At>oL{wM`V~v2U%6yx%Sg>Jy!oP$D}*kOY~@v5_)yWEz{;V5&$(>s<iEM`Z&E$r3eefGRbb26LA&631$phJR'
        '0XHWz}C1RIQGsUDh)gmZr_39ar+bCwT`6J(OQC4)pGS%&#l2Ja=aRXbzt2J2Nw~sP*hZcF4opTncszq{$Uce&ETl'
        'H;qoImZCy9+^>`g^&+<_!?zQA-'
        'n;mal`$MPFFyXi>)K%oJ5vpFD>w|_>ebv|G_{*r}4)|JU|7zcpCMOo|A^^voVXzW_PV2_BmP42(vX&96wQO@9s;~'
        '{%hJawDd67&@P?XPV>JZJd37KN+j1dG&Qm+D7^(6I-Gac$BXvx)^HFw6@fXN&A?Nr-'
        '&oc?{XqjqLgNsV63^?A*b3A+V+0$!?i6sS}+n+!#}3#@e*Xgp{Jac$KRw^2Cm2thJ9t}oj=mHKIMmP}kq%q351UJ'
        '<xS4Vs*F4TH`L@5~rHy*EGKH*#|FWLGn7PFyUMT{yjDGqO+{C6?Qe`EA5i^;T&Nf7a>?xi!@vDJzdb&P?9gaj7M)'
        '=$X<aw>IW@rS<UjjWl-~DB4-NL2JFO0*I0gz2eFNW;IRbt=k>v@}cb<Nq79!+6;%9b#qOCuyCd*uI=N;#!%$p*_-'
        'zb00p^Ai10fVtaY!Bvpj;p@`pumydb->x~-I_LgnnQcOT=<v91De!F=fzv-ML6g4eO2G|(egJWlPwO%Yo60IyCcY'
        ';BaCN5e@{mU}VY5QrlOzbc7EOxpu#{a|%Lqm_j|91)2ogb>OuplBRXXaU_!?!_-'
        'bCB}{@NQg}E8Wunku?P;pNEpOp3@8S$q7Lgsb|B(4bnrqXgd(a0%;@;=wfyVBO#x?J=goT^V+gF>t?`M7aZ4dL)V'
        ';X76+e8R&!RDi0+7<>7ePhZ_hAP~OBb29tnACs#oXU`$h=@>Uj!Mx>Rn{s6zM4Yg18J9#koH}`+1R0e~oU!-'
        'jIDMq8Q2JV)KlOA}n%Id2kcNL6vAw^Ud(4y+u|D_%R@7CZldXoh-eWb`WjQ*r!1T;~`Dx@lZ^t1fPM7?J82(gyG`'
        'p4c&r^E@BaB?R+#{;sDN1R0k@w3p<KQvOURxVq}fH4gV+m5dvJwC=LstksBc3|ME_B@26X*TifS%;)f4z;^&9FaO'
        '>`mw|}~Kx^?IL-f4GRSE&THbsJ%Q_v4*k1K_s4i?+5-d;P5t9H8>~2_tg#e2X0>Egp(Y2z>J8H8buTk$v;5m=b0-'
        'b7w+CQmY7Kv*8fW;4E|3i`d~J@$sR}B&O-'
        'C$bp5=(7k&WyJ*tK>ZbVx2EuLL5RHY`X@@qX$+cQqfyQ<<IdR@p@vCu0a(RWIE157~9$c&UY3y9@xJK?!B_(F)u%'
        'gx%fEeeKERRg9>U+be@-~#0NSuSf8AJPH7i?@Vb0*c~m(%TsK44e_+wLlS_!m+*(-'
        'A0a$;mXw(3Dc=Zz&hE*(8I)a+nvGECsow7rlp~A?7S8qEQOlAsiOc5)QH{w2=)HI9jApRz@f3bOFU6BJ;(Zk_%*K'
        'X%CjNy^gIRxIcX=keSdUf~sU4DuJ`SB05LfjL?;hkP)$W2Zs=w3HB9VU0Hd0>!DC3C0L;SEvJe<Dm+2pc6vdCJ<m'
        '`xqr51mFh}rBSO?(bFp7T2rWweiG&)W(x}X=mJ}zM(P;xVx39SJBo~9tvwj$UavmxwFWi(Sv(Ve8{fE~<Yc3e=(o'
        't`)1AdV&`MbJ;tn!d*YvfY#vs+ug{Ul!EQQ{bF&1{@?!(<R$rIiup<+lzjJQH-'
        '#t%ohca4A)sFI?X2|<hfB=W+ziP($aj)7R4+t1zC?5C30?wy#TL3KX6DEH}{}ad_aa5`+cvDLD>i!Nu+>JjUXjg$'
        'Ja|GuA*0p4DK*xFBjUzB#%CjvE()qT_Ttk>MZD-'
        'gf;yIe+WR<LSbr?y%o?^c{(1aXpO+RbJZliKX6PyvgD)Yn@m`QI6&#d8auR-AB7t9@Eyv(rQ{r_0N;SU<~gjR*#b'
        '=`Y6c<$x7VO+d7ySX*Gv&tFBUgYJFpd5uJdGQi>fSe!7ZtRvpl_tT?YD>vbNae<*`Q%`dTG-uP@qd2C5hC-iHJYq'
        'FOuG#(vlOZ!3jBxvu62Q>AW(6juf2C|Ja2N%y5|Ruj&?;IJuYM~Fh1ePFYS!`6<l!JyHM+BYN42v9|Fcu4FJZ<Fb'
        'VQui34AU`3^Lx>8axm;v$kVuo^saVB-C^fNq(Th21DAP0}y=9mz%4C9@EX>`oAmbSP9u+|7eCjOmnTIDIk`?D|-'
        'A{O&S+#G5c=9GO<>%gpY*Wnojfk6PuDubx2QAXthcp&T#pT!Ci5zIKt&bXRA{7wQ(YQH)s(qHhyY4>AObQIzFpJH'
        'ZpJh-9nicGXDi5FL)3My-'
        '$Od+vOakVdiv5jKsPWdyR9f<>5XynsYhf`apb3JGI}&t?l2I~4k1N=P%hUWqsS~{hXno#om#>@aZM+pLscJYV<8c'
        '1aAVpHKmf&l|@W<`uoXDSPH|GoH%k1WQI+nGYxi#<C-'
        'p*NPzk%Hxq_Nq>YudX)Wt5e;pN$?qmt*(>x`4|aLP2;%;Q~^0M0}2fN+7KisrI_<;3-'
        'f_zwR*}5Apw1gdY}S*fRySB_%Zn5tbG|?7xiQxD8XWkyhYgZ8+?=qzl+LA?tMkemn9h52Y-'
        'i=DNG3_`(pZ>;WxW*Y4maq-YgnVcu)Hsavs2pL<uwNlNEQHYv3PMnZRI+3-VJc-'
        '$cDN4iw*F*eUihJUz^RpC^iephb?tVa;?(?wjjo~+tF&$$$J1QoKb7(*f@@F*Q8i^&{dyc4shK7@$1A?yUVPze_P'
        '{sa*5T0MUFEG^dp4TzH(Lgq8M*uxX9iW>?k$x;;t9tM2_t-'
        'R8{!oXci0c8M!3TWghpi*e_meq==wVXe%0f?b<Jx#Pij&G(kMpaRiYi&br&}Kt*aszZ&Smq|!h-'
        'RP7V8yq&FQen~{jk<z#aZgwO74rm3j2@Ka=)~W%BNQ-shewz9L8@`WwiZO8r-'
        'gGAC`zWy^i|m>}kMvCuqbgeZ(ZbwrhpP!?}eG`LG0CzG!gR7?lZf&x0MB^%~xxYqop=OL^+W>Pk`m4k~fptXI-bI'
        '1UGB!(9tu{^~XWOLd@2L64vLZID%6`q0prO5bwUOeM7tw~7P0m2%mvXsGV#A3mN;#9m*ev~I4rHd9_}Si!1Vtxz_'
        'HP@_NwHOA&zV}P`EYGbvI8d4vFbvIf0MKV1}E0@0H{YcdEFlsCXs6A*TfJBkNR6P}cMECCgzEV%Go;nF_yuexieu'
        '3%@eyNZr0s2&5$zB-$4=$)YJNEVDisgk&vLt*|6zAZ#={PM&>*fb&4Wm%Sn;*_~7f-bVceoGZ;C-'
        '!5>iJOj;_p5$Wl?DF*?ji_?)V_?$fC3CMEG}HgY5(`I{0y4(`X_O^dHZC#;aopns}v8zy|I?&N-'
        '@nccV@9V@_HY<ZGR@8mK=T9&^I+y0-'
        'Q#3MT1EIvvTQiBBm}tWO}dha{`v=Q<zR8_SnDAhG$WJ0Dr7UHg2*mBrt{0V$}ve#T4v$C2KRen=K&nSt2&)3fK%q'
        'D)KMA5nX5i3Yvse_JHec{U+e01QY==EAx!%RlzQ-kRP|dhTKdB0D0d-'
        'g@<T4pKNN=h6HkR}O#3G(v49&%h%6=S2o3+)#C99UyueOHwzgD72k#EJQWXj}@Tip!AupIqe*|pFzUu4!)3dvk#Q'
        'D63%evb)}ouasJ~a+e`Nd{TZcNfI-piNUJ^|&6d7E`}4F+#!4-'
        'MxymotvuqfinVl`pXr1S0!aA)SSJ8Kt9!!LP@tsCkr`Nce)YJXjv@)qkr1kbC8J&cexfGui$)+D|UaGTue1z3wz0'
        'HFLP;cz8OdY)bCN_>uEgb*Z?HkRk8=RW;W{vQ23EYU)ovj1MNP~eb%%9?Sn$&9>FR?M4_-'
        'M(fz`l*GmI4SZw)o)>;h4bCsP)C57@&O9tJ>$AWMWRi5fPksJ~X)~{4DovLZVzxeR0Lpf6Td0P<)dEpJ?&9^dQON'
        'Uq%V?c8EGPNY3@g9Px(un(8$9?HuwLLSI55V)Py^&K4rEt0X<1-trmc5=m)MM<fO)QG{&AmVHOIA`t-Jpr{v-'
        '7%U0Aj*^;ZX*an@FugfyQM0rlH&dESaw8Sz%VdthMwHV;b&Fo&B~(d@8E9Al6SS)Iaz>%a6ekDrqX4AGc-'
        '(@Sq&PQNifQ@Lhfc8wetQn$R`B(D1&jq`U)v?@Eiz{`U7V%#e79x0rSucJ=-Q53q6=7zIjx0IC#>)q-'
        'F!;*@g1=2^^`{%NORqhRsa80$B$JV88JVX=BO@G(5uyFU~_}=@PWV}qURvgkYB-nAKVlrZVmAu2h2YGYid=pe3hB'
        'Y%Nq0PEL~&r*5aw3j8fEVg3ssm%i=v<OIZwy(l4kd66%|%iGr%1NlO&#>B}gI&lpqHUIcLNzP6IcI{S~;5T9g5Py'
        'JH9Qi5-QFQv}-1l2se))ZE-{6Yq>8<pTD-@AK}5L2WD3Zr*H0q`g;hRI||(Yqt`<cA%sC5&#-'
        '|NJ*0?Aid#d~V<8*<DaeC?gmn^3ePgL&>3P*^5Z#ViY29`}8C&RR$~(qrSNTt|H%9)sE3jv5dS_eylU8dYW`PeR~'
        'PKqXq<K6kyQkb7-'
        'nonMn&$p*_x(oYFs}dMbZDd>|6N;jShBARS7oQl=woJC}w~dPL9e#x8Sv^CGVvsEm6i4UkMCz9^;{#yIMneBtzFe'
        '%AL8kh)Ypd}QHN_ErKUkrt0jFP6Z@P%)e`sWRESCG_kfH(QLw78SrTWxE9uKREehRQ4bGC3Cj>kYvHeL?y%+0y3F'
        'J#hBdM)DZ}>V?fZxTEG#kuQ-'
        'E#;gNkde>fPt*?;|h|L4I!z8egnsrYItNI{<9t?7`?_cwnb*A|w42N8(@(%a{6UcY@mc=Pz@{nwA51;OE;tyVkQd'
        'nof9#&}%Eof-'
        '~5B3&V6(ukfte*ZYyi~jN5>sLKG9=Aq09QE<a@g$u;pU|RtvV1XWSy;4tXx)1%bg(uD`05>ii%;kC+3wAo7Z(@3i'
        '(9?CIJvpq@AokWl-2vw*ZZ&EVuOSDcl~>J?v0YT6UDz9ZEfG)9@C#&$#>&h-'
        '_f6Uw|Dv@@%4CoC+Tm~pZ%Skev;Ck!}0d^w)k^v>&~t1d+{Of?D=2cyngrRx6cQU|N7$H;K%1Le)#b{blvaWy2Y!'
        '#eErk&m(O3lAH4tZ`P-'
        'L|_XqEuKHh(hII1M6{a(M1oopZXlUpP9bV|RsO$B#uZ*A?2t%BRzg!j(Yc;~KFaOXA_q~o0g@nr>fsl|AFyaQw61'
        '@~@?g7mxO7Ax42SdGWy(Re35r0*61Uc7q${O#kX?_a!r^}pWW_Fw$z`TmO^U%!4f*nj-w`95-'
        '$e&|qHe0HPwO`eswuoUPLl#_x|R>waiup8@wV~{6<VP4Lm<o!hor<pVs`7n96xT*(FU%&eP#Sg5*A}wc73>w;Qgz'
        '~3jzk@o-Px9S}lI3-'
        '*M~43?$Mm*V0jfk#lHv*Ja^?H{ZHimjF02@Fn%f>B!=rr6#h)VR?A<K;K*5rwB$kCW^G$y@$6d~#PAb?gXlv%R28'
        '^<MvV18E(u?S2GHdBasVG6+65~(<g~I==vUr$zMLx1$19sU6MOl?-'
        '%0`w58fVjt#v~q4gofgeulDw6T+uh*urCYHpr8e)nAYbw#^0|<*7vgVdxF^#zgt50v^o{L0(2@0J22NL*}Q}gw@C'
        '~Oq-4wJQDi~t&GY>nl-=~*94(nGjZ-JOI!i9`0{MG6U(X2at^~hoN5Gzc|JVO!iPc$JpgU^_nXMo)M_*szgS*imZ'
        'L|=t@3YHv)DrF6tKT1m`Ws`NSDO$(&i^K45clX|GIXLfRFeHw;r^zYV7ER8!RUP!08TFr>pj}6PSEM06!+$yFrM`'
        '2+v{-)Tj(6m**I#6$`4^5YlGMU{bwq7)dNxTd-'
        '=0BNv9|C)5H6EWzM71q&&qP&^*mqL@kNoX@aDL3C+iZW?R*6wdjur52BrR)D>U9HT8S=*Hb|H@x0Y<x1)bC;BE9?'
        'CiBxC9CQg>y8=&35Ts(sBM$TAq=R<=1y0e`szYxcMPhlkeTq&2A1KxGV_2jh^`r<vVC?`24nCyIj*tk4NQKwOzks'
        '~$p?i3imM!WX28ghGWjcR67k+1H%e1p*icnNCNVa2I6yS%y9AaUu04YF`dj5H+@#<ac)jNRjpN}T^qOUY215L#4D'
        'EkBfag~7J-'
        ';;Z5q*B&OBCUvS7O6xHSa;L3ARisv5;*D!A}nix+MZ5FPfxSSs3p0y6$`T~Y{^%I1Bija02&PjG0aeGO!IL&L}{@'
        'T0g1%`HtK4nNNv$tkD2d-LU5sc8BP`>m_k(xR_?#hAhDJq7w(K|80~hOWl@*-$vsy$v2&wa6Gp>-'
        'L)LekF=;jLMAG8kiKKbNOkzHLN+z2CQ}Y=GUE*CjmqTmcx9T0|muV?0k-'
        '}jYFJ>d554EN_zU74+SS;)g^*REvSSmH6>;eCQ{A($ht`O>hd=p}u<>r?ob9kKqN&!fumXO64W|Vnk@eeE5^<nfa'
        '`wp~xl?NIIn{GL#t4E^BLI2Px*u@QzH(w#=etl)(zmnY^@dW!uvS4$3_xF+n3r$lS|A7r91r`}Go-'
        '!n5Z|#iLl(jXRP#wbntH3g&*<!2Aon!F~_Fklynz+`3l}0uRSk!?_q<Ce$#U|N~L&>JI#T=pFu^)iY7@<xqd0k9K'
        'Cz4}_8Wv2V4hq<orkY*aOGcyTm<44&D}lLyEn{KqgbrE`GYi@=O1BN60gNOx;EomqRRCj7=czjhkz7A5_Ko9B#FH'
        'Wnd+ZpBpfLpr0<udk79|HPkw*}`N71C{=)ozkSc*L$FIs;%sJe7K{6jlLp$XIs5J;`>ym+1rPyGe1i3B*i<2R$<1'
        'V_5#+YCvK&2W+?MXMGSSweeZ+u2;@n%$KhG?s0vkd|_qU%VG4R+OkIj-(Tzfe*C%4yJo0V-'
        '*ZJAkamluUpzkt1*Qi4i#fz-'
        'L%b8&{}p?*AUsxZN?DeP3Z}Yp1Lf6jgTIKiv22+bc|p?CX$j1M;9@6n41j#`77wlTic!J0yOmeLZ}#j!Kax(okk$'
        '}cnnKheYx9S%`T7pPUiWnrjMTkef%iyPIxE!6Ys^E!_#b(vN;qJWlf7u7h>Q02!{ZT7gKQ&jIfkHw}ja;A{SsfR{'
        'C~NJ_{^1VTqjsRJ~^80-'
        'oh$<!D#2mD`uC2b?5WZR@uE6>S}81pR?Z@A9*hoO5{`l%1;yZ^LYynAc3PzL>sX^`D*UY6pSiFsd6kdnf7q3H}D='
        'eoAfL0zbDbb&nAGRyOO=(_hiUAkVQ;@eOdzh`KiDF2{JqReTtzMngQB<KUs0umX{KQgt2JK}4$8W^&nL-'
        'F9fy%~qV-'
        '5{mgEa@Z7a>Rc8zZ&%XLJCXMKcqMj!eW&<}PT)2t&+s}eUm#0pK)u1>%<kmJWICFpMafx1wRF@S38EkiqqFTuvSS'
        'HsJ_<mOeYRDe2C!hC3Ie0=j%J5y5@=~IU<Fg0OBAi+wx!)vH3CHF8Pb6e01OfOV5v20VJxN|6#0p(LJn7w+(^p#8'
        '!>Qs7`2x@qcAFv=d?rdjo$`vCD-R}WbHV>OJcp)-'
        '+x}&Wd5pJ2Dd8(EknRpwdJWwkV0=D!HvLfq8bE7%m||@2;M0l_26vcs@}szInU3aCe?Y=6TeaIat8mnD3WC_E9u{'
        'ssMfZ5sTOggMfp?Sc>6IG=M%DFql+i8H-(B@hrlBfh7aNe&RaCX-sLL#_y56!hgG;-9a-'
        'naU{s!q3_d2Y2A6|F3+#b&LOh5KuEsSCmJ72Tw<P+V=yqFQ{TKi&A;204OM+klU|c~jW6T!iY3qiCAAAOA!j3OzA'
        'GoO#^=)J<L>AL*?zh?sv=YW#I0GQ#!O`suqhN<+?;KswQhO8<%r=0z<$!_RrykOZJfPE~j%C?aAa4agI-'
        '5=ak=uvflpNT5Q?S`ipcyCLO|##{K>&9S?TPdj2|Y5&j@6^=+&-'
        'FH4k6@@wrYpX4|K5PrcGoMd+}p?b$GRy%R9tYARuf9aKaU**v_?p5Qecf@i7?fkk~=>rAR?DAEtDI26DF=(o4L3g'
        'yv-Yqun6_uuc%PR?z7%>CO*sj!%@{YWC1I+N-'
        'nmX&EoJf^WW2w=wLiQA_KJe{NeMi&d~>7vE9;<zLvAYKGI3+BN$k)Zm-ZHrs1iu~38A2dS<?gO&fRbk$*|Vt?hDQ'
        '{zomPKIw{aCE(Zir1jE*6u<|ooSy>JvGeMnu1l0w&f~W4K!iYlGvbZ6lM1s@G7j$!zvo3#d~z4<669Yp0(o$54oe'
        '0KOU1-!V8bBKmKqJ6I4<m!k2}4Yw{osR1zyjS7W*bzuzNFBhsk}=eBGczF?T2O52>M-'
        '4g;#1IDISLjkLOUkutS@@(>>rG+zo2%-'
        '&i4asIn;L3ro8@h8`(AO_}YP|UJc`^r?Vf}6a9tZNvhje*J^Nu(2^8VT>jvhS{SHYIXIIkl4NRr&S%HhHt>14H@7'
        'oKg@p8;$IQ^U_R_WnRk+I5`&l3clQnARy4#O|5L_jp~0i|#<{U{p=pQ(O46BW}GNqo%&#7FUB(ZL8eAgx9(7_(kC'
        'mGe^J}Dv&GSs_ktwqG6pPAs{27mI5KZ2Xul4fVyZm#oZNu^n8t=2?(tV5DdX6o5C2SlX;?H2rD&idvV+jDPC+I1e'
        'Ab%xtg<jy&eImU@mzr_C3CV&H0KR#Re@qr>nU*c3BJqvu3v3b4Khu&h1IpHJYULIyY-vt3gs_Urf<6*3G)Iwbevl'
        '|F%NcCX$7iA}NgG6;gz0vqCH&d{25v%32jIHBjEWrR`u<jms=FL<$&KiFs`|;2zmStz_D#kQdH8Ws1HDF3U)l1-'
        'ezlKYC}$tWFe}R?9jz<Iy-&IhN}4u2^5V=>6Nl@*<fJ(YeO>b-'
        '?tUpHzYt4dRY^9u~^w`>=Pb<sQ3!rsmd6@t)Cd5W8lQ<Z^2_>UW|g{Bye#U2g9}U+{Aqf3j-'
        'Gav#)Kg_jeEl3Ir(-'
        'aHoVyQE74=C?wHqXbX5MY4=#KlnjNEOzP0MoaUcR*o2Yr~0^M(b<yG?j^pwF(dFB3PH(z>o_?XF8}(o&&%3HLb|P'
        '7t?km0cIWsE<Ga*e0P>Cxhl;FELtf%}O8nI;^Ru)i&Q`W#$yW@VoYk;pIVc&N6=X#gqNB{KTsd^o%*Y!_3J*%oVX'
        'q?fCidsWm1J_Kpi|mjbnkW_ZzAakwioSe_iX}!csj}OSbK#Bz1`@$JD}TPW$`B*=790<;>G)XjxM|Esv6(!Jjr2K'
        'OeUZ#-s^)d_}#X1SYvlDdy%?45gm$SrT#@d1{(jU@YYuzvH>14^$&rY-5j5p4oVp<M~+aAe0@cDt>6#Q#p<X-'
        'Au}*R+1ZH}F~Xo>hA)hkxD=mKAfda<D)PAcATUvYf}DxiMoSDTTs9Qf*%~~nE8I77R3o*PRU(4)^OA(VP}b3ziI~'
        '~oXq=+tafjhAG$7j>!8h=;(|P$ld3@TdOKdtta`7|YbXsOGmsPA~VJTcg8w^p1;6ps3NK2cjq`n(*yVNxhJ61q7w'
        'Xka|sUfZL+EZ4Va=AT5+Gg7hPb8BG8C#?$l@=u9Nis(VEls^PzdpTuNy}3ahknBGO5cTpjMadN1R6nwnFB7lw7|h'
        'n4KBId1Y84Vu0X!q@9o@YmFiJq93Wk`x)A{A;D6eoi&)X?-'
        'X1{)bOah*jDXp>FS`3y{;>IXnEfPVZg_$eOCJD{1V0Tk@iH<n;Q=sJ#0vgQdb%h$)Z8O?6{4(QJBLY@8iRv%Q?V2'
        'sDx@tTBRNsgR6QsKD_eFTmbK)3zglRHm){rp**~R4?f~gq47RkVd>P<Z+1hDlF~Ksxmu@rW*8cOeoZj(u`t_n7Eb'
        'vw-AMjG~&r<M@Ypo^ol*UZEcVn}5^haQ<{#|6wK5(ZX2e2MAx-SO#t@xq%R=AsyK;}cK>b6BNx{>K@YuohVO%(`G'
        '+?p$UxA)9T9!kPD>Tjc#a59CSFRAC7h5(lWBmCZpw$kp_b{jD>yT7wDF9W>@qp|HIVY*zpT{0qgU5fUO*%%s%ZD}'
        'SYuv|p)G(>;%o$2W7E1|?cisJnkZx3I_tFN!hOD*qp0K|5C)q#?w7W=&9sNMSoKDXisZDGpe`uwEwM1uZVsHVVv$'
        'n5M(aSBnYqjJrp+TCP2Jk1L{{+z)<NL*z2dP?kWNBS8#!#3&@Ukth$EFbl^(3Z_Fp)u<@wIW5Lhf%-'
        'nbF+wJM>)s91f-'
        '(TQ!oFbltC^OBpk24f~qx0&Rc&BhDh3%<a*#ed<Tkr#KQ_oe4G>|v50zL1BOd?$5arqxk7<bi}hHxJ6vDBS+o6hF'
        't!O-{@rcMzA8y!%#EPX2%3ct`o8b48M9HY^rxVLbw2>@@+W0d_Ek4mkJMYXX!8K174&H)`vD903H1e()HCc%`5z-'
        'aejuj?X+x=7iUsCR5=#-'
        '*y}*#Xuo68<VrkaMFpXbFEazR_S{=%Ec^$RD)lh63uI*whcMhMsRAa4dD#lPcxX%<Vn=3B0PHbl1*PNyHTr>LG8P'
        'N=`r$&i#Yrtz2Z;L=&VoA-'
        '(Kc^c~;f{LrlH|JG>Y#rJpi!__4Q~}4!3U==OG`W2w>As}rae>Gwg6C$qWu64y=30%Znf9q@lQw1c^WrD<mr*mYw'
        '8sOkLM~~e3Hwo{3}q<))f4GzaAxJgG0j`K@`Tf#%v{wbgJccb<4nzv6VeucBCGwXTji9ebDcSGso6pNT4qb6&kGr'
        '1)9_O8Z=t6u|uajV*JZS18uB^DCqY{)-'
        'B;Lrisk6;RoaGA)SMa_%<U&Z=CSep1lRt>O$RU>uzT=nIqj48tF})XkH}K60baWqoX3nfbmxMp0*NE|7a@OsQXp>'
        'h$&>Me4oaPirI4|>)X}qB^(Swyo!e>6-V2@FaLyXb4ULD?YF-'
        '2rS5#`*zm1)rVuc0Mmw%jg=`Lrt{vUjoO79+u=ux1et7IG{hAtf&Dh5_I&SsXu(Hn~m|V;-'
        'xD1`<9KC9A_%?C&fwG5kI_l~?@Q<X|rajDK<>|l4wA8m(MEw=cpnS$wH$D<=v-'
        'CV9n@WFI7JdR;+^*J>Z*w%2x9sr4(|kb=!Qu0WwzPx}4!6-'
        'F`rZBY0>pGwBS(}IR~Q$|1&y#O&>>6)^8Yak8uqrVbG{iZl;F9iZTYWVO8Lbs5L|v$gSlU^`>ZoTAE*%@Vic+J#1'
        ')@V9{BFWGU-SNFa{<2BzPEYZR5TmA_&<>-'
        '*H;RzE_Am(mVxb?fO0Q+X(aB_+l`+?AFOdIkrbaI7XKF!9o63Uu2RHpUX)$Ok2?9_IK^o-'
        '~aXhJ|a&<`&@`(RCLg$aoREVvEHWvExl3Sx*JJ_TMoN+tHx2o)?BlfV80s)u1edDzP;jvZf?Z6G|EEUOl&bsw%43'
        'dKZ%00y<JCYPYGH&1G=HZPmRsp_L&klw=XK)6_i=eTtQJo-~WJa*5&n-cW=*nsZ1v#eYLptU)>xlqrdr0<vh?_-'
        'iC$Fq*4+Q#651E)CbBI&ZiC?SlU-xva<tGE)VN#kI&1t8~sD60cO|5fe5fU4!r`CQ<Z7UJIqg93eNbc9!X8uR@QL'
        'O{S7Xyl!G!sQGBRTzw#0->xnb5d(|^?zoI#%i{D#M&8qgedoyE02l4q?sO#_-{KgLC2mCVtsHq-wDYPH#KxjIbLZ'
        'zV|j4T;u-HX$##B|=y!E?jzKyL1MU7F*r`1l!nmE&@{-'
        'DtEc=S#qL=NP5FzLIwqVg=A%COEy$#<cmRgl|6D)PTf=CZ*v(m0*~WM!@qrXB7G}ne0j-'
        '?2&1;#^|KwF51;U+N^F#i7Jyivjz#0=VK`t!uCWFILpYc9B0H=-'
        '8mjWQCV$Q*tE5(Lyk{Mo0E<P0SmO&`RQCFx@^~&ob{ch#I8#*y?RQC%F0sl1gK3~p0ZQm#KyRpCqqgn7^=Mmm4KQ'
        'n-_rk;SG{eI7&i;D1QC~15XjMcrK#S6<Ion$0x=wC`Jzl^{D%&}WZ4{4DhKTr*P#S3P88oxn*tGG&B`D&9i2z3tv'
        'MztmW1UZXy5nNBLJwf(E4&kubQMt6WlLn>&@bLlK*)VmPOca5?Xmoa><plikOgMR&7UEQK$Ty)l3-'
        'V*EYG9EqqtwZ{)dpk{3(r1=q@xLo-'
        '2%ioP7`m@b7N?aEz9^>sfqmm|s~hmf3uk>@$uF`lEf#$SXLG|!qfi(;1!t)as#DABfN_FymC>i5a!C7Mt3Hv!4Hs'
        'e~P7#gKxFICaHGa;~&xB@lPHYs=$eH@by}d`a~qNp-'
        '65^_5sDB2PQWyh!{hN`>G<2SGvQj!sJsvThYz7aQ0W2w}^tphJX1kY)J7o<3Gf2{d)WgF!SoOF|Iq)5t=Bg(nkgd'
        'kD(7X6?uMa8Z6X?2adkVy)~It=C+Tt!%GhHTwuzc<tNSM=+-fenpYHeb=*1QQ2Ra3+>jO{(YXasp`-'
        'izVvT$5YE;dft%~m5__q?i(v{~T8-=5X#0-'
        'T<W;d+U#^$@cJEfFiFf?<F1idtw{DYGrDnytCXg?URJqDWrWH(PKa?G8b)(K*9FVJWmOnX8TBqryR=wOv4|T00gY'
        'uv%kwYaMZ!2f{R{T4(@wg$CMOx;QbILzQkocMU)(vCI6@}$&k^%i<;mc^Ur~<c{A1qy}I&-jKt6d3dmW-ZHM=juj'
        'xQ|(ulzs4yo3iVONPr4PQKm0o`V`8{rU)W_>keoKQFXO#6sqg1-'
        '9`*dHA(bU`=~CKVZ$hfFCC(QRSe%@UWIn_hC+>dvqf>jVtgyI+%$`?|D3T65*1tTL6?2xY4q6-1g6-'
        'PnMZ%8(xczKcL6STocSBO(V>KwX`7#$+WnB1-J{;}(MH~MK3wh{7xt~Ibe8)Qdb%-'
        '>yv;q|Sk43@nD7wh+mFZtY4@m|<s?voSwd%XjBaI(F$HB^W8>_LlA4mj^X4e5cbi<r^G26-9d6(;7wxhV-ocU;EU'
        'f~(0)&Aqw{0RM#fP-0!|ICmb6kfgFSl=lB-`HF>O}bFK)?6h-'
        '8S$&QfJrH{N3>0y`<ldwb5W}wE~PyVsgI2QB%Kr#RVJ#A8rrCFYMfu4HP#KaoRb{^Z6+~soC${sq9%C!)kku=Q&<'
        'FFXK8G61#dpLE_y3;#EPWJPPVf6v`CafYnyJ(eJO8yPe*x@#+C6BLzMaBmO<&z<;IJKY@N$6e8%qLf?>&Db%PNA9'
        '1_#DQ-'
        '=SnK~>?8U*!3Qqj9~(pgnpu6~9)8ZOkVLxpR}mDz5!43m;e$)rf!op21?G*EJV%2m_vM3QHvT|lPq$fn~Q`}vSz+'
        '_B;jT47b3K|Im<bl4L;H^yG9WLT_I;Ps`nu*gcZ@YETg-`l#?cENwt*w-ZzGAUhOlB6vwcvdl~G#99!OWOkC-'
        'P$7yv1dpOy^WEj(JsiV^L?+yG54%52%DzyTd|FZ{aZ|I+utkAX`1hd&h90K?e7p(7+zV-pmzq__Oji(6Uh@F9_;u'
        'T4~BsM3i{*|^a%^?kGgv&FSy<P%E=9`N^NYU1l$!b^T7XjJE$|5t=<lBd71qRRrrKFif~x{mA|VQBkg9J7;opU9C'
        'G*BaIbQ7yx(74u87j`$8PWTconZ692XCzsf?oh#SVsLbsHG4|1=%WPm)>by!^wrw_8=)TfmB9)~>xFeBu3|mlj1{'
        '43^HK)?$?25wj&&xjYj&MFNzFBC=}O@>TfmOTR;7*RjtAUF-UIsXX@E0qAGhbWz$HP<<CRNYj<fw$X7+lp#63v*T'
        '0)g>U!)1WzfnLaR(Jquch^^Q_E{C-SW+Zh{LYgkzgE{T)u=Lb4vzQ9n|<I*5|_UsBVmV~#R~T^8vWe$AjRZl{-'
        'h+7r<}W~p<_{%)o7r?8+^mU_b1XyA8;_jc}$nFg*TYCOv4@v7cJ<;Jqt`T0Gfm{s;DMP&qSgBbNgW+rma+;lLqmY'
        'd8xa)su+-JqWlS{0M&C?CT_+-2eyeTp@yMt4VPdYdg)l){3Z&N?mdjRCO{hk`Dp04KpY#S~f-'
        '1{A&OL|!c@1+mGBlEpk1epD8ZuY&Qo8-}=Ywj~PoXb{Nu4qMShUnlauCYSBQFpo@<WxkkOQ-VVg`yYQ8E{fFft|l'
        '_ugv>Ot8|`48iK;vRckiO-'
        'D&IK6bIu|jJ9u`dsEteE%7z{Z=~Sq+<9rIOt^|f#w^s}>Ez`mAiDnD6<(nFld|q2YLLVn**#uwQ>*9NtX}4UKbl`'
        'ddJoVvaGJHqBzt8dF;t%g&v}yF`7k>a&O{QfR&sDf=C5l^GiH?7_eS7=f_L!?Zw4X~g{Svdaj<a+WJLR<E04;{Og'
        'rw==4vEv{QrIIbF&CVJ%ZhaeWbSw}vO@2WKbKlRO>8Atl}o*$0*bgGs8WIy47uU1yQQlF!`E{dhGmzsSG*J@yK6k'
        'CNxFveD0HrwIN{LIds`OpO0jb3i4{c5krbCf`9awj4mlC6ZL3}o*NEauscD^aN#b>G*taw`Gb5>{b9$2&a5xq6V~'
        'a}<%2N~5>36G#uTCs=k?^FkFgD9fn38sOI_m%Xz3;Z$o)p?zg)oOBj9l1a4KHJ>3>0dVa$9#hj#3iZJ6v-'
        'ynv<;*>nO&1M5}H0kQ!X-bw<>R9T(<H5$)2V*N8G7>{75@C_vlFpoMRBn;G$!69REYdsww-'
        'W3;~6mSQX}1IH2M($MkcI?U-MuoMcbGR{d$0XN6VSLi;Z%TlVex;A_Zy>>*k4k#(-'
        'o~;ashm9grA$V7*|B|;vaLydg`4yKyx+7Vq!{3QDH+{YNX*z9%-'
        '(xbjG{Z?=rscd9_vHN%{wHof>e00lUexzw<+2rHSmAjZw_P_8i6{O83QmeED|o48-'
        'P<!vhnO|3MMt{8&G|>(gB{V`lDsMeJr}qoo8YTgUtdv=y)!rsB`2xvG`6bEp7!DlbLqm8N(nfh8_XUnjCYgJyBgO'
        '_5w`VRzdlFU&Yj;-A}}cfoQp9^jgRLI%(H7wx$vt;S>-'
        'W?O$4JmcjWm+Frx%>EG5v!t@MkeC5zt!87KozIv%HX=FTsWZRF_dE6rr&hlHqf1u9Xd`SZwm|M6o&SJkxEM5|ubg'
        'r<kvZRi2-'
        '#v)!e4eh&T9P9PMxN2ukIjq)1v=Tp?oFe%}UE0t<AiN0nGYjWi_BXm*Z+kBYvYZ}v)jNTzN~~CO>n&%I0R%aw8O>'
        'Sl4?FC$Sso90yK$Zrt#0=iEo9tby5GBd_mf638;TK??rs*;j8qz@$$U|yABohrW<tJ=?rw%2V@5q~4nzKDi`cyu1'
        '+8cWCwy>gBdHv}LmHw(?L42uG1Lg+xJeG;8b>tJsz}3nm0!Sg<#YDRvXR+XU_V3ncrpR)?w7JFo;RR>Vxz<2Pd_g'
        '@ewFW9{6#+Q)+a}H^ZiHl+FIXM2er~Fv{M4r(btkLV6&7x(5q1H%k|``p-'
        'l>eDd&%;*%=);zb|0#lp1n?zU_*>&_ewl133b3FsLMg`uXd?Q~-P8D-7~&&SaWS4&%0CZ6!@xz7-'
        '60JMvY{AIS&ZnyodDMj=jmu9Yb`;F@Y4I2M)Q+yYH4M|iro(5HfVesVHN^_jrDdfoOK1w6r2WoRcoCv|hbJs=`Oo'
        'eZ8L$6j|U{1j{*`K@z~Sq3-'
        '{l%fv*s2iuKkc||L$fFO2*rS5B6Hv|P?G)hU#Zs;McNEHtkFs^hW_R?vudh6Kt0T)l&v3aO;z>G}67I?J#i&(-'
        'kv<_<OaVV|+}Lj2gRqJ#1xwP?)ostAmDU(>(j*_!I>U!tPo;yWtDNIv$`W*{7f6Bb!ZET&LKN2>ST2|nOxvI+zjP'
        'x05N-'
        'H0_xe07kR9yjLe+aI^iGlch^zff7S*|Ln$C*+7^b8<Jf$a0>zc}{1GLLJ`4dISpU}oo(+C)pt`eUn7|N@7i&#Cvt'
        '!m(URZg-G=_EVN^U=PHl-Pgqr|0`GetiA<*<k<iljr;I4ou&NWM6uJk*1?8jrka{)9?t7%rjhg%62+jMI%^&xFzD'
        'LWwxi|CmfoJE(g>PDkUbS0w)I)<ciL}zIqjchb;z+68MHFHcTd|lsxSf>DwH<cuTyp0|A-'
        'p*w2rLio|2*Xc!mH6R|xI!DS`Lf<@`~^#d-'
        '$1ecThG~0<P87$^Q<7NIH=Nw~9kDOO<V9h*JbQgP+f>&h2@~~F|8m*R4+sGn7D;|GCon$)Dlhzf*_SZIh8qsw411'
        '!Q|XVTSL8Uo~<FRGy8-'
        'VTJ^XaM?I)^1neB~Wl`18Rh?3xwh3KQIGxkjwSomH5T&4trwoO5Wha?~=3GB$b){*jwsB?nUiya3PgdbdVQ;F}so'
        'X#-3)(mCWsOo_0k;!IsR5t5JDL3}$eUoa{3n>zEhHP-Iwtz$pRvC{ZZjNzAV4$YP^MYV7>0%@-'
        'I9g<Ovh6B$%^{YL^P8AKAm<w;7<{HQ67kg05hh|Mfy@Qcd^7=RE)1#7QG1237?yksW;o0OLj{nf;xeOj`>fF@ZsV'
        '{;Oxmy`s41bD!HoJPsXNs*q=uBp8Q4%;^Oiig2aN(pwAPkPx*`ypM@n|mWVuvmO!4NunNbH?k#cg_XMc&{Dh?c`i'
        '{+CJ#?61L<4bugW9T%Kb=^lE?qdT?iDx)|kyVw-_{L*Jse|Nh_C!@M1Uc_LU#fs>qe4L}a-'
        'F_^DBM!p7k!BhZT_{tG=Ss#z-'
        '>w3^Tb)d~Fs4n<7*88ZNcaa~LAa9|Id9He)wWQ#`hC}$9Mubrdq!aP&rJ?2CJH83o2>TVk@gczG6tB~&pc5YA<dh'
        '%a_d_LowdFONOvE7sm#wMY73;Gt?+e^C>pDsY4SbeL@z6xF*Z{??2YcFH!?^F%9110a*Zs;==Fv_1tD6*9M#UD%g'
        '?<*&wM`14x)%k9E#4HXcn;VlEVVfl$^8RQtexf~VY<Yq^+!GVg`~Nu?O;K5!b%=%|5E(9m})x2{6rSI4ss|hVw<e'
        '1p|%UcQAunxeWiqLOn40;O^Ieh(u9yDG!lE~lT~2jWHvyG`IqL~U3({FU4AcsmUKHi^|nEF8^aYJn5%Ji0_{e4eb'
        'xQoskHEQ@L_cn?o-^hoPeeX`=vKfv;C_<=(^#3UrcaySI?h)-=Gt5-2xihU^K=vir-'
        'HROUN*ex&A!#I6!afZ0-X)yB4En&Yfv-CQa0)Ic0U<$={xkwQeWcAy9l4w4%ViZL*;mHGxr*D+x3WYarfgGrG#>Q'
        '9YYSSONts9;fKbfHMekt$m;VY1M8iZ_^1VZ0Df4r@l>atd>e(TPaw>ioHTtS$5TY12-'
        't3HT#9C65cTw*fl!_tN96b47`0*CcKw&YlsJfWHK2HVqR&Oy=8_Z2agO;IPq<Ypi7i+jEdz;0Q4^123wVqlx}yL?'
        '&0k!p~N}fd>+VVv}0W{Uuk#vc4xIaBkC3<GlEJGdyIx4qBxtuN0dniRts<Y9A`y2e@ncKllF>K8_}CE$SGwfWH**'
        'R%FvV0eYo{jhLDR&mdD69->9hTaxtTcgZ1>Nhkq$|F!FedhYL^@2l-'
        'hxM<vmP@fe*5ds#{Uwj@MD&UQtgrbb|S*p_5QAxW1IwP20|<kB<=!;@6gu)TR<q<JMCC$*V{m5bLd+cgkg3NM$^@'
        'i3c#ZjvP^Y7<O*kwBw-nnv_yH85c`%0~EtChV6OPz@&*bO4wY*?BTt5_piPJ<E+Np=;P_ZeX0%H4O!n*vO|QQeO}'
        'meMl6ItpETwXo?Mg*UZKv&T}^cuO3()^VR&h=ksTS3BdL142%Y(I^{8rM^6!YB%zZ72af@Yj?-'
        'bXC{s+q>QD56i+)cS84p)S=ILGQshj}WknbGTI4~qf&34<H?ZR*C63nKsSSSwNQK0%hl2YDwD0luq=?`YLz>Z#|;'
        '}o{+VLFg{ofQazf%mGN>{i9%$FC4b3ZH2nFvA`!lBw+jNicQC-'
        ';1ief6k~m27tv}bD+EoQ>!28S9IUxJIG2<EXyGr5~v>S$d|AO0h+)EWi&rcBVkdFN@1-;o{`{k+8D~ZB{$3-'
        'GaW*#Hp`0b$y`aPVKxvs6YFX$*!#M6(C1S$6Z1VEpfFsl6P&9FjIt8zpq}tm(>8${Nd?B-'
        'NOEZWTCW*ArHz;iP8z452!f7>j)ZfJ3}zz{0b?T7QpHm;qVSRlJj`e%0)O~N@r9fn%ttdY%V%FitL>_}dc<0&nWr'
        'pTlZoAo;^?ZHiIlg2W-`Xo&TgqP>OcdkKtyPV-'
        '{iGpsD^aC$jB^`eJFuzb1RFIs?OPA1e5w=<z2t(^?FpUiw*t7ckydwC03^rH*6Lq&~CIY1qe;IfP5M5il$k75Eec'
        '+1Q#d4J(2$PXXgl_Eg6iMoscl*@><-E0*d=mwkkorlpn0hMtWOb{W9jxsq6^!4kuJ6GQ_tW=69L9d{E`H$BZ-JnT'
        'ISa%*Ig#BZV`q3qoFcDL!Jy-'
        '!>+0hl8)lEGL=CF*d9)i94Q<BQ!azF(~mf#yW#iN;%%;9;v5GSu`rf9yX<jBTAVs3Vw?e*jOHkk7#9~J2GBHUapo'
        '$1_?<v0oc2=VF-u_e9uHB+Z(DpQs@AzKC@bdBc$l(Bt6GVILf(8dYW)C4WeP0llZJY@}`yF4yhvebW)_SLFD6T41'
        'bLBvx<(MqLFQcYeMVareiIK<9B4ZL)3p154oFOt;u;PZmvt9*+g1R=v8<)BupsAi)##zY~ElBkqF70ueF5PVpc!P'
        '+H$1rquvtdNq&`=a^l(729LgK#UmM~@5C{L^&w@d0>}K-'
        '@qXGQR~{^&gR)tF<>KrtDVE<Spnf@vF`Je%a!zuW<AFBkX?xEh)QF#-i|IvAr0`0lYD7D?4x16G^ip0AiYXT-fes'
        'u6te~BP_?=q5{;EUCBhVrSujgzBtPY5x%W~7&o_<)Pqs1_7wSb6{kxA!)pV7CGl>4}1J^1fne$_cMw)O@x1(?}a%'
        'uerR@JDl59eg$8zp7FZ&tR3pLAjh~)8RZaED{lm94Vu)i=I9ODoN6Dq>U}B%&Bo8>I+d7hHmZdu{cJu!<U;H!99='
        ')f;b6afIP3+NmQQXciHJPc%U^Y8ySbOGpN!);#Y8{;ufAmZq&8-7>`et8@8~7)NR;U!?O>oXBg03@1?p4thv-'
        '$YtcQZH6u#9peK|tHIFd=iUV++tq))A6xV|KEqSYY+tNy{B1`l1EU-0JXy?Y#*8a%!<K9%-'
        '$+IL9ZZ&<nbjI)4Hbo<$Bv>_rirlqKt=!&kUmpY~v*rSU^HMtur@=LZ&bxb6IWDTw10AG5AK;`oN#|=uRe=tjW!E'
        '`@vejT2>Azw>*LTc`)2ei|hMiSBW%!1z-'
        'xhp5bMIOB0=I3P!lp9NMjJc+So>u(u<*##fNyJUI*%PA4jY643+j`!)s*m|1lf%Kh}<&6Gb50Nb}&jYssXqD@Ce?'
        'BdXcFYLY_Nsgpk)58UGL19*S{-'
        'zFefjseu(R%;^cUaD~xNhQr0#VnUvZ=ny;^2(=(Qh{vWjxergI5iB&6=YEMEhDbR9K#~f8%o>Q-'
        '(G*M^9smY*57;b*5r6mN<2TM+PlZ9qC3OSr%j^V${A*!eZ#Ga_8RwHMA1F_=DsEC0@!D@hZ+js%RikUL*3`6)(Bq'
        'ODD>Yi1jLH?!^0vv61P3T9KzB;d5)3atw2jAVurC;m6~DRjq{hJ<xcJnhQZ3gAuGY%5pWqx-'
        'I>L;?$KgwlvYmX;IWpxEjMarI=#R(@pokBQhO0i|pR&Q=)+n~}D}{hFt#fb+I~!<kyd(8#EgaC_LH!#J7(5P#%vO'
        'zo$bUHid5nq=of$t6=Wh+XhUTEZ7nz6`?#M^e(Ke?3xcpPPgrD?Z+Ckwjcc&q{B<*;ZbqO;p8Ow_k;e7Cq?_R&^m'
        '88aJ<7Mjrz8_#8!b{-'
        '*J32fRo<RqyKlpIN$&@I^Dbb`JDDl80`*2CRw!jT<$6IdS7|MFsZez9*H1@UEZ@TXU551>s12kD3I{dp7!N44vN;'
        'H5Bl1sqo(n%iW*I3#$ex-'
        '0ycb=$?64;j%3X1tFq8M$SF;UD7Z*VS<YIO*^rInsfIQk0)O;E2wt&_6uiHv+AAD>meb;z^wQMqT@q#C~l^Y-'
        'zDK_(Wy@NpgUFgwNhf%IoeR49V|>e<#w+1QO<yn6rq?c=BKU%Y-'
        'bc>m+`w=W;>58gd}y#L&504o=hkXXq`{GoLMNw%zfb9N>oi`-'
        '7qLX={d_2^g3({h?$$b43K$wdgAVg42IX;$RF2zBCD@oBYM*_qi+PUn>5_$oO&&PV~oOfVfdv5&_9kYa<kaSbj`P'
        '6ehEEbL|>kyNwOiBzQKGMUR+x->C8Mn-'
        '$nv*F}?uBl=4r!I(idKZwXUez4~23N7RP7d1M?H!XrixTqOy3@IRt8@FiPQQ2SZrjVI<?};b3QL`z`Gz|k_9Ak(O'
        '8=6Q7P2(`wfzhTr=y};KFMYQ0R_zlXGvM|%k_hPZ-*YX|BjME-RmEkK!399@Qc0rgzi2s?INZXYpI;W0bw_ieNZA'
        'M`M1o3Bxg!Yw@N!)H`#95L-)pRJRXn6J7i@xInPw$S*z}LZ#%;DPA2iJF5afpv-'
        '!L#^Q@niIJ|Bvv!8B<?hse@&MW3&?S}cISR-'
        'u1bhk<hIN!5!HnKg=wKikzwi_B;$TSTNVThP17f6HcmW5n(@ClYNshBDoS9tT43+&1AX-aN!o`xj4kktY<_K?OTa'
        '|!6dNQKE)ljODUqMYYv=unIf;UZKGJHWs8k>O2T8+^t;^w+C^_l~$7um%=XuQVV@Gy40`e_cZZeH0xiCn)z;p`+c'
        'S#N7s(yADL4F#gwUI_*!O{P?PblrBc%(?dO!&tX?F#IGGj=-'
        '=EHMnWN<1~&~q3v*D*tJCnBXm?QKsdE#6rG{wG({8V?G)3DJUY%FV-'
        'g!P*$aK%F>DJ+z)X%PPTdhAD(ItVU>nl4Wv2xjw*N3i1(@R4xBfaR?u5}YG(4(D5t?TvAz}T48Y@k=+;1VY2*pA?'
        'YrF!VmekA_nt-=wiG6<Oj%_U3TEF{vUn<wBa9yH;2O?yv5G<-'
        '44oX*^XDURvVyL(tx)D)L)Hoo#I85AjMflo;<1M$4ZDU5v-eqim-'
        '`piRU90Hk7@#us1+Ce9vPJFUQA3|dhH2kbjK-_Nf1VnR6G<*WW-*Rb@)1E8Vp6BOfZTN~-'
        ';<7?*v5&kxR@p)HUaK7mWWizMhn1@5Pdw-#rIOImL%U{F|E|Gy@3u}KUZnxA-_UB!7GGZxlIod(I=#W{bjvTk(`h'
        't6;<1C;jGLS3`%jXhM%VxB8>7FOIhj60vUgcyjh&Tel&AXSr^yn+yHdzQvQ`gw8eeU)?5le++UrNG^QspL{8wY-'
        'a>sXK)Y@LZR9G(W-H3T(R`0Z7A)%gFG3mmOcechmcLVQ=-'
        'MPKBwKKNf6|2^NjjsEfUG_B!?yXS9<xirL)V(uey)sh!vWQG`UX%M&bj=h*%?E7{kbFX<2AcaUi5YP_;A72L#d#R'
        'SJO)zn0LZGsRB}LcTYucx7un&eZxya@$VYGC&7VcMOV1+Q6VD>t*`{X^zPnTT_JP`Frz-!da~>2<u}A-'
        '3eGftAmEPnvgkxILK4&&~B|&GF-!z?kKa@_sK8gI@emh=;q|Vw)8|2F#%j~>M*<(?N-'
        '4;yOC#Ku(v$z~;Qv%1h@0Y2EA#AR6HNT+MB$V}k6?g=*4))e{VgDM0-'
        'O%2%7WxoYW03&Zbcw)m^63s@ss8v?ydq%V5hdh<D>)a1MKDB43OJk*SN72?T~@x3!*>ow%7zM=P|CQILhJ-'
        '@G`)=X96FsT^?WiNcCt+C=7o{%kf#Zsy*iHu92!n;_@R&B0~KE8|Fuu}(EO}>!KfBX(9)Z_PWW_<0t{}w(b8Yly;'
        'St6sIZy;ha<O$yG1My`PS-Vh2{=NXf0&}HJXUMgy60pjhWI5B@a8Udw>-'
        'Kt)GL!Bm(lmr~4ZMq{kW$*qwQh7>CBe)}~+EBa?a7?0PSg(R*ZDB6ITAN4zjbk3*!itEHg-'
        '#Wh#fo?NTQoWv9`7{B!%g;wI$8;x;h4lqmi63%om6L4_Nh8ek9Mlnpn9Mo;`GI0&rY1$kk@Nehgb>Wp9SpoGJEFc'
        'U)4PIQw3>e%5(ZnxITgjU^@F=iAw{%0X5b7sz@9FjM(R1#d%^V~e-'
        '(P5I3*<tu9K+82@VjfZrx`!lw;d#mFH7L?@o9;*mD$4+>eUw}ia-'
        'B*F<%89j5!ct{f9BF#^2<NGX7vb!RqGDqVA(Iy?BE+WcYy=SV^P~+vMhLhRuGWQ^#5r%X5L*t#C#4lBK$G9}_8=P'
        'hCR7L<S4|HD+rTVU2wNgXPG*QN6TkxyZtPnvYdJD5>rq!)~g*MaS7?I(p?Kp1NNP;y8yTnM@4~Q3k~OITc}^ukzS'
        '26r1K~N<=NueBrOPQHWNg!%z8*+FI^-p+W@tlBUQJMQ)qMpU#kin-'
        ')4epmYrQOG#d8D}}eT!|8UpWm<l;;iKp$UCDSy>6k>3?+-%@`N2nwSlFhq?2XVq)px0ks-'
        '!0W^WW@XMi$B_5T;)Q=$+IP-'
        'H=HcEXhFNBA{d;x>L34tmNARnTXl$9<_iWQS_#X`cnxa6t$f;I=BuYzREGjI&lFypeqM@5bLwWJXR+-'
        'y@bU?2|B9)S$SEGAIUU|h2m=K0RI+4?u6GORS?|Et|P4YR>q_Rx-NE4zKK;NlnP>xiDwFWlzHt*MthpjMN&+GY~`'
        'bX<|pCG8W<u~A>FwoQ`KW0LuPfQX(vA*`E(h7bwqbJ<DE$|i3mm5N@UYE-'
        '!mjFENH5WcIC0j5&X7FRpISO>^B%?$;mV?(G(x>dnBz@TwK+-nfdoK?fW%;7hcDX-vxGxPX@Faz)dD-'
        '+(u{ogIH+S9WR$)JjB41<7^^QWyAn_fS1^Xcm+g6ODK)h4yTw*k{K?%!-_OTB83-'
        'XpvEx7>x`+q&ykr%<hW$CD0Kh&Vk#bW614;4qQsB%K1mJp(pA@RF0w@O_1a~`wYZsQnlxSL6-'
        'tw8MqpiaQ<_Fm*74(oL_tsh^4eY^$I6Wy_LSfjZtE?slE7U#okWn~rDcc^TwH69m?4<W7XJ~ZU_cr2^;NK!6+1Fk'
        'RPkRH=pDH(tZTIkg7{jzEGo6n4;cOeYX%cwy1GO*{6Lc0(E<t0t|)b#LglliRgGkE9MC<)Xls03ZNU*(V6i%KuaQ'
        '@Jfr}xSlw}4DPV~N&?$WEnIYd3$>Yg_Oci4v^7W|5z=kdiDfphs}iFsN`PQrWzWH%_E$znqKmGV=k4=j6t@;i_Zz'
        '$<c2ls_yRm_C(Dipl3(`k0)Zd4|>E3TN6D@s^rOg`!Eoppo9?owL4t7j6Fmqgo_R1QHqyvX*LWT=6vtuDmIBDWSX'
        'WiPv3~my+jCFa?dav{_1cAXj)FPvr9~TAnBafR-twBg<7M*HP@J6gbW=Ih1UQnj%0^K?JAi@B`E_X<~$r4TA%vJ*'
        'r0Z)#F9pb6v8qYE3kI*u22tGjakLO-r)WR1n%qIBLh6+xY;9eo|CppB+P#az-icuh4E<;bLNCcrswC);CHloba|I'
        'S*#bSS~{lDO<1AFilz^eIi8eZ9y>AYxNN^DW9GNxL+V?3A>c^iwTeU%CadWRlMlf+7mbx{eN;QpKZxhfgvb|*b1z'
        'n_JwE(HyO&QX&p>6?jsMl<na{ne%_$1n=o(^fI3$BLVEQRAoMM)jPl{qKVk+pu5Z_}8Uz}A~X3$smg>5vG8ltfIm'
        'h2HcH||Hd;$696cIv<(a(CgE=v$t(NPIJ;=!~J=3*hsuXOX_WGQJkVAdl(2bP$J#k=~WrfY9!M0onM#4#s77)FB>'
        'o8AzGr(ozgAB<X1MwDg1%#6u%l<+g;+EsNa+Yphh3!UOz8QTb#vXC?*FmwI|wbl|1AX|udGkpOLOBG;<E<t9&nux'
        '9eDpwda<v*Dv1OcAch!5(h#QK{Jd5z7lJPeGUIX&kpmScFv#u*|KGlTuY*Tn%W1-'
        'F2^C4{@^`g)6q%h8V8Fc14{@D3Eub(S+qWGO3Hgz>yKGfdlh=j}O{MEoQ7GQK#PSUj1#+hyM|tWbTV?jowuWqY_F'
        'SFRd@{*t+tJ4p6RNUSa$$*<C)t@~Gz~dM8E`gL4B{Jp8cQlO-'
        '8>Ns>#_O!*0%5fIQ3WUQ@7>)xgYyV3A$Q6QPnsF052-HC@JJq#Z{F1Y6n3Br+2b{8n6oK9U?r8v;tUd-'
        'b0wwRyzEn`$W2)$(*a9&W440KLP%EinN+1!TJ(2v&7E6p=Sd8iIE=QL|6sMXcg<XCzudcIWVn0_Mecv?=bX&SbjQ'
        'O**#Zk}nXUthghifPetdt*?IvrAv+^2g<IZH8%VJQ8oGR1Io<N?kvjE^ohChQEgQn9dERyHeJA6GYd))?N1&6yK5'
        '8<nFca%B04nugpx6*UH<niuAQ6>8OP1PnQE++^yN*tSf$<Icr#?puvzTU<aHrg^^FiS}Sv;F>#xE?zwpWrOWDFrD'
        '-$mJLI-^qawD?B;dsxJTKp{e-'
        'p~{{K{0CT{^+Dr!MKHu=dfY;5D(sGggY(x_e`GcnT!NM2TC9g*HwL%&qp(ddXaZtkt${?V}=XrrBOYopYt*L@6DW'
        ';!bXVY&+LOwl^mI`G)H=8&n0_jz_O43Apq6s)1BajS?qjk*lWG6X@=FSpLP7+f590Y99rWF?uib#A<c2UXc&CVNB'
        'LC-2_7PShs6m?~+ZJ7}$8omJ%8sSjQv9C)CSoGIx54!Um~3KgrlspdTe3^-'
        'p)#d8jL@QTH^tzLH(Go8}o6Y_(P{RGceo9d%yj=Va-Sh8FJra6HL}ACzCLPB;0AHewT|h`+tiQITPLPk<0c68p-'
        'DD)eZB`0aSU9=*z=udhrTOp#1K&=!k-bkDMrLfp7VwCAa8k-'
        '|V2ucTv433bZxlF~z}SEI=CY)25vq5(D<2>Y~~d7IycR=L`m90@+!lE{|>X}#MuUuY$iev-RNAWIL(G6)0{^DJ2a'
        '`z8CEr|k<y**0rv@s7Ii8dAa@E+T$Cz;C@})Qz?d#ow3oH*_R#<>{k*;aWTz%DBk{b5_IQIxLll#EkT(pA?66XZ;'
        'X;cRX17br8dAK5VayJ$y{;YP7G~K;dw<H=RSr1Ob~r*&91N3*4HtIxk=U^!(-XSMRHG>il|!@gIHuA-'
        'RNRJaawg01{eq_ABR=M~_w}?KxT-<%^-f1n|g<@4EH-kICmFlTu7s3V9RgfbR5~8Qx)lMmTJbmTcf6JxfmVDLo>j'
        '9|yRULbnqw-N&9Ir>}76upJ75m#<6l=Q1{-'
        '8_6+@%{mletjHxsVo{vPlK#TLk;?;(B`z%yKeBW_)<l!I>Djh0VpYYHz(4E|vU2?AuY8v*{cs0fu3vT{`0w(t?kN'
        'r>=NW~ejfUjchocy;FW5R%|1-'
        '~pL|jaV{(&<hQ4}+wethZ~2*)LC7WhoLFEIv91flNST^IT6?{Tp3E%jy<{r!LcFR)|VO3o_6`jJ)xj>IK%qn0ci`'
        'I%I>zF=r|nxyG?`#&<YT1ET%Pi<{5DMF%STJ5a-'
        '5FKX~Ghk?aWCbbO>08Cx3Fvw<Y=~Y5iYNI=Y{%z{LYciG(46udR78WC_A;%4-'
        '~O_yCEsoQX2w@v1zobH9~XXU8H$$Inn!mvR83^{s<CHs`#-'
        '}>E`QrIS)c4cgn{lx2loDR$ZI%>vjPv&{O1lF1HK%o)A9Q}pUgAsbll`veBW^t`%OlfQHq#PA82-@Xy-'
        '+lVY)8r6f|vmM0a)6JnZaQR_Zq-nEwOm$Y=<|U~1e&3l>eypKX67A0bE8PH6jNo^_OMw4ckXQT<9Kuc0<^Rfkq@q'
        'x)}R{@}<2>>p$v8?lk9>z(U|{k_VScZllTiuLn*6pK61Wo;{c!LwO2X5;_pxMd7i28KS%i&PDHp39YKy$d5I7T^1'
        'FNa1<`xJmxRgRy&x;r1BISq66NEjDY)`4iys&`Qk6iBig^X8(DChtLV;@9S^DN!GH~cVA5D`g-'
        'XeF%~i;sTq#)T>U9<ym!yVu?odfJsMoyuOpJ^G;4ZS&K?1b_;lie1zDa6BL}bClU646{;Em5D*n<hs*7~qnhrJ$k'
        ';wG09X;HWtntk^Yid5&i`>_wg=mm?Dxa$d(RTZqxcdz4>>loG^OWFC^-'
        'nM0sZoaqVYgj2X)8r(7=l!6*z3r4`7{@gp}L1bkzFiJ99_rCed7la?UQ(GRY|>$<j!{ZQQ?qmR!xF03Lm|3<<1fg'
        'F8<m?#S^n}i7TWCR{Y=p^}oWJ66=^WSu7r7w66HHvXV%uSBk3)S<GC>6DFybh5w>7bNw_khy4;2$}rOE4eg-'
        'Dd-)PAc;SZX742Zd<@ZH?_D`VR`g4AojnaLof7&{(Z*74gC)0XC)4CE42J+f_19`X8ZwDUlMtYPg&Amk6up-qm<y'
        'aQ?`(2swUEEYzcc{|A35pv7X0QOV>Ba^eblM1S>J?raFCE3g^&SYSJH~&&E|%ULz~oil9B<`?r|hI+6+IPyNB8dj'
        'o|et`uw>XX!7*hu5vvRjwH5CX?~8d9g!Z057PG88Y<Ad~WC>;03j+R8PGkjSInN=`s;C;aSjCtTCu6Q0^|ozBnd3'
        '!?`G3o<KBxcb+4EXA4iS-AqtrQ!L&2CL{3q^278^P9AZmgbWcA+AFE18zYK2<vw1a@Q`Wz7bx*nh%3((H>0o}6z-'
        'TMeY_bfp7t_$cmnU2Va%fLNh-_`)V69j5vn(>N^L4H0S_agai4dku%ia)7aC(IcF#AUmlwxf=JwbGq8&}7-'
        'IR62XQ4sU1=y{5HYk;el2aUnFSHx#wvi)$8Ehf6P9uH#m#D(KLzPQ(t%^0n>oi>~T$O;zsK`F>da2}P!Dhu@HU98'
        '{R+)7WHv5FfC2@z(}EBg#A=8=@2})452)X8CGf7dPw0Xk*8j=O-'
        'tVR9kU6k*K$)FlpDgfjBp{%Ixr%1!=Ik(UBT^(RLs%0EVUjbhX{en_d<uz`kQL&h{FZ#`x6`XfK(!y0EG%8ABMw!'
        'eLohwx>I%kSy-v?2*d1&S(Qwg_XtwQT4EeWdsy{L?J?lqZVwFq0^d^G~Ap#Yz!NSb_W(lhX-'
        '~ao>J+!>u}?iuO~YGLKe2_AS6A9IH2aHQk7Aiq>n<XCx5R|TQw@{RM!3cq{~b}!@LlWwC27lCVTEFZD=sbPng@qf'
        'VIU84|R%Eg_8M_bigP%E<qKWr;&E)Q_jk1ftszxMCgnIRevDMlaq8HnldB;*D5z7_s;Anj2CDl&5;5{=JR9p{Bo9'
        ';i$Y?9Cgs2Xpa0iZ|M%5saW@c&%K-'
        'jwt3Mmg8B%K;KkAVIu9K*2<E=s25F2FH5hAlaz*d}d%ng}!<y@hJTltIlDyY=J58}6q+>uhlZJE)rYO_rFs=6an?'
        'D{{EH@ssew{F+o+5?NM2bfhrw*!^ZPnlPkhtgGDtyABpuoLy$E)1QHDoW-2Va_ZyPXb1%D-'
        'A3ct!TS_XsMvJ)iGkyvb7$GWMq`l^g0fK(FIIUl%I*mrH|7wnz+&Eg#Pxz$N$KVfq#yV2%rsahJGNzBVXO^lqSRH'
        'wVV@gc+cUiocBG_S(51u;|=_cDY9q@2A%IU16FUL)thI{#%V|TX=p5@!qo0L+4@)-nE5Fg)VcmL&ZZ-'
        'M>Y#tW0%$EgM&fvlJ^9Sro$vZx`<I4cXl<`4AV)~bbQ9h{Woh7AgKI;9AoMDIX00>2&jBqyf_A6_OXay%4;(_Ui;'
        '!CR$&VY(6`^zLKoqP)$2E}qMCXmb#J4xn$Uiyh(6;N|yjwOWc0Id}uGhr=6VTQ^vb{6WIUIjn)A|fkjkq+&Q{a4&'
        'Pf8v+@AeR8t5D0YYMWLf;6&~>>)*=};B}6nQI)4Qe=u(TfDpK^YT%)0_1b*%O%yowIjcm8SKJuM_oB6yT8u4bD6)'
        '!_f-B#Ef?NjI9XAAo9U(*-495jRrIVk4W-'
        '$HrS`HAO$a{g(b$l7O1<_Swe+5y!xub%pPnq^UyLSR`(Xhxs{SpDsBIn7b?g<U<)h!FDxcR!2halOfH2aWcl42JR'
        'd*U_6HI<fuXPWqxu5*nWdc0bjHb6@_#b?8m)+Kw@-'
        '$j?~97F?`&m4;P&0^5($3*u+_#lZVbu<V$DD!*C{8*32car{gto@j8N4H{k0Q|Z!)PMTVi$rGbgnkeD9pT<?{`6l'
        '&kiC5u?bP<>-ecR#V9f=#wLEKYu7yb1GeQMVZ~OEo&Xc%uGu%oixu=V>#f09fh)(FFA&NG+sHPT!%g`-'
        '#eUqhsWsR>>&=oX3OrgFk)t5#$$(m%uM?ko2=7sPFDTPNpSm1bRNA9jfANmDfv5-FcSJo(<-'
        'ioZV)yr5>q7YeVfe+YYd@^WtPnhG|+L=Y>kXRSC?}*6`!-'
        '*%OY$<by?$WiNVSxz>ADqD1(zcTw;a>9te1>x<YojWzj#f^ZG3(0F63-ub&xl>Jia&^-Yp$hk2QR#w5i_W-'
        'M2Sd$u^u+JH;6lbH4U&_<>glV#+P!~>uy+XO42$g;ya6nYj2t)TliN@yuiL&;w7K;Qpt4m1x|OPz+Do44akh<7=6'
        'wwr1dK0vwQ)oXg?dzz06`s^BX5rh6zx20+8yGgSk~dDlJ&(YKoxJOJa#Mf_~gp7r_I>a?;QmL-'
        'g*sHrK};+ZZ7du#2f8G~9*r%p5(z{g}+k7@-V;R>UtynoQBnhz&7HrXzH(13Z$VOffKFftTY^`pHa-cy!8u5q%qD'
        '^msT2^@(s0+ZkX8)FOP6$q<zc^xrAb1m2SG;{MNni=+|nCi@J>He)#^g{6d!F)s|zA;;{ji!<o(ZHitq(-'
        'Uc@EY$!(Z=WoCI>i~RSMugp$;t9DpYJxay#+ICdr1X_FOS@)H^`%ACe5$~<M;5DA)j5-'
        '%wp?sLsa#a+Ub@S?f}~!=q?Wr7?{I#_oR-'
        '6(!&#`rz9MeR%5rPbn6%~3wqWTzVPf9C&WKkfxRayK4L0%_R(DEmCo&HAX$rip;hhD(7qk^R+bgzNU$SH_9>rup|'
        'oR?S4|!=Y(u}PF&dQn27k@jRJco_@%KZoJ(|P-'
        'G;2M)VRD~qhHt*(qRRAn$y3o*x^7$QmOS!EqSK4<?7`>?JcyWVUIaPYemG$#5*6f0$Z_Ub@7lQ`Hk={kdo4C%>{P'
        'pA9`A?MCp21T4G(BSj5qNtCV@_hA6^PAg%T~6qqtdROET;%Y_1#GZj3jXQOi2Mpww)~p(9z%%B(uA6=^vG+9DGl5'
        'oGMgxdwI@vHsKP(H<5~p@@g8L5toya^5IpFUI)}$Lh8apJi>rNx(vK=UIiotU1d{r_Ad)JX^P70zLD|&#;%FM*jS'
        'g-qYciO0r~74$)Xe)Jw6}U^<z2CswK?<+=s(k!%&c+TW+c?-'
        '?9EVGlab5>#DWIF!TYoU#>2dB`wQg##~nW2lmdu&{4n^$D{QDtRypUaYA~u&Jtj;~GCxNfNzDfuq)Op%NJ~n7}!p'
        'RSj6Vzu}A)L)p+DuW&v&PsKb9bY&;mm%QO_&=9Y=twBjTP^eIHjQPZ@`DGwAe+-'
        'h*c|r~#_8q61cT?WBQ<gg;envKej~KV*Z6cC>$_65Zt&CilgSuzM?f1yd+OB)#CYY~>d<uFg>e!-'
        '(udnnHF{yGZY%e7I*SRnmpA6$~a%2hr^U{<4#>K>_j+nB5Ykw8aKuK0mV8}2lEjKA^c15A-'
        'CM*h0)5)ld$sUwU&>w8!5XR&k$s;}AEE2$Qu<GAoqzWg0*eu|5P^97-'
        '&Y>oW0JAumvfIO5W}q8(qFZg103y(iYsR6Ld~*6|@4%~qfBzq#+U`lshmvko5ao&GcO(NZ*w*AlT^xOk_Xmm-'
        'I`JKaJ(8;4$BUu^n?<epKGMECjHj^1K-'
        'FNxN3mi1_8i&FzA<b*K|b{OnXD(aI?(CI>i8W3?F+g9NV%r&?fl*Y8nyT_?eG7`e=%phcHGh1q(=cpTd}c3&;I?t'
        'v%!ZMc{C{hd4aJoXmYHl>N=<vo7cl-xR%)oLd6ROP-UG73*#)B3|N!($T#iA8brg6*k~q}Kv_EyR~W1tMHBF~(&j'
        'dIW3#WsxxltBb;U!A<%}Nx*zWKYT>%nkov(V~X=R~qRR@N@5$M`Qjcbrb+68FM)^$L`A+QW;J9IVc`e;gnr-'
        'I83<Ko##29VE*lY~{EZ*8biR;m_cI9rr(QcsiNsW74ap~SQp8NSHa9Scvw87U}O7p+}sfm?VlvUf#<I-'
        'F#n_Kr;c7PchN1V)`0i=eRB5wl)o^HaHrmAg@&L~{u{9CVE#_~*PM#A8d=00Ay$`wUZ6^kOH|tQ`F$`v3>N(>xzV'
        'Y7;|rvnkRSpISmsP29uI@WEditP;<RSikWR2TpnTW}#<<kwIM9l!tG@uh1ox6N~k>Q5aS~c;DrwJ7i%0EPr1MuAs'
        'buwl0csO((Z%IuTyGrmOY&0Hfa@1$tCREn%w*^`|Y-'
        '12<bEBim!!Tz%b(NNtVNaMg!vMF;wN&466Xr0Wyw$I+Mmpa0e<cCgvLBza%DTF4MXUouyr=F0qrxK&?5lQh?N&=R'
        '{2GY!@INU!&eUSsI*G%@Pi1l6sXA2h4}=^ddBx@3N{d*2Q8UGE9aM(?+ET%o<O*1JN7U7)?om4?pA!YP?G^lt0yt'
        'Cx+yT20#(clN@Z;9uFZ@Ai#7EBJgD_Uw*qT^{t%-'
        'L+uGH*a6OdOvvj<KwsQ2R}Z4@xzbrq2ryte5uN+^ZMnR$8TS}d;Q8(ynSaoRPoh&%uoB57th}R2$i<KyBGa2x_2k'
        'K8Ex<MZr^vV&IA6OnkJ)sxWFAgaP{A#XB)aRXwe-n3fLks62*7|Ov%CEA-%fUD^m1IZMj#2$z(!3%G=|b-'
        'bBcx>GCi(PsS=Jx@)XJ`xyMooDd`u;=PG3d={W$7ps{>$-otUM-Et-|Lj0q^&iS?>Xho)eXt9ZINSzFtcA$dRaM-'
        '#yH1ds65(|%O(OP=t}6@{^C5Z+$1%%~CVf3y@q777N1*82et);$r}96)f9fKD9pR<Bt4Yj?9QKN{0p>1Tp^@k7E1'
        'q&h*Fyzu01Eu5-J9q8Ic89n<7ltMqvX)`2R+KKuk?V7jd5m8E=>c^7UaE=kSbF%O_XwNA-'
        'cblWk{%(;y#|-Ts>p=xJXW9Xsw!?p7id(sh_5=pmhtcG5jZ-(qu&Yi-O@kIm%a#sO-lDjq`lo7>KCMfe5f}8@`By'
        '4}X{L;0`?}3wsi&(k8$~jjo)D!@%RJL;IRwJxD~x2ZUeQD;-'
        '3KIw+#X28gW(Ni!fcEg#+y3J~CGkxlB`XiGlgDp*>+-'
        '^z^X#IY!l@xoOQrR|i;=W_*Ofn7;}77jZ+8za8v>x(|;nNDgP_OP<H2?`o8+eB@=OHI5$-'
        'S+ZJ*_}~(Ncx9uEcnxR>c_7kp<EU6eky!z_9D9>yJr-'
        'a*WL0oolIi;PNrf*wr*GajoqN2(|wA(o`ifSx{}#B0=sxe;=A%D+;@a4frP1e)XAME9`a$gR~yq~aU-'
        '$*DU%CeX>u~irgOco%a49r(J@m186NA}iZD^?2m@VRHeA;{8N)hJt$pgWx&B1eD3~1>Lqa4o27QwximfJ~=Zz);9'
        'n~;Br^RnL6#0`r3Sep34y`5=mg7yJoGS4TLc?tr1c|}d8@M=QD7Ii(^=sNNwbdP#LcvZsZ^P1Hsu~OQLFIXmm$2k'
        'Wgon`A=V^hPu=(=h3^yk{dz)`>#ce6&yJR)3*JMRMp**YiouH%p0gqA9x>8(mrVR@&I~i_IXT8PttG0mi;3fvh%;'
        'pboJh*wBkCyoF>HKW+@J1ZRH*VY*3_$H13{WGE1&RaAELU6<8H{v*RpY}O|1bZo+r0'
    ),
    '_portable_underwriter_1c5a734b0715.reporting._core': (
        'c-rkfYm*x{a^LwYCd?O(#HDs+>3m{L*ZCA($`!vN+m{b4)_9f#cjq*mp=XAxUF-J#R=($#r5lY$<1s_-'
        '%66qHQK^<B9*st$(P%Upjq!N=b-fYgStSl#lb1<;b=8Qgyc0<y_I1-'
        '0)m5@>>RpnTjmS55XYIOf#3tFppJLq=b=A(s<MC)D3uW2%&>b3)Wl6Ea>PcQzb(hO>qmfG6<=r)vU)N<R6qNjOtt'
        ')+<@AuH~H2Gfqd=S-'
        'IQ0Wbz)fGFTi~ab+>#0ekB6|Q`7MHrjcc!K84k7CFFRD9(O?BAq?~=Sts=ZFy=hX%h;QxN3dxjbLWht^lwGqwxrs'
        'zbIU94Z`pMLV<^8C|_mor1KnN#Mv+m*WAMqoye{jp8#>Km~WRi~Soj1u^lb%n^<d@Hi|qPV*5#3s8es&*<f?f9A6'
        '**?E3>wGgErH?>J+!PxeDi?=0D)lW6WZO~OZ*KE-_f_4tI+v2a&Wq~Jb_@LAr6Ys7NpEGduj{H4w+g6YCFl*5&V('
        'ucn7$O%{?N5<PhQvMVOM?I{53D3CsUQS+viQu*42+yq44<8f+sBBG)>*~<bAuByx)`iR<wswfrVxZWc3YYeJL@dt'
        'g3Eyko$|ss0Uf0GSks0`|j<xfBx#t*V*@PzW(ByAHID3{anwkW!p7V_Xqr0t&&CZLBbtx8=8K1<GD(b$&G0DfV6<'
        'r@#``#c8M)GwZ$xlVZra{7f6nEf0Y}gv4s2Pc3-'
        'z3NO<o0(A<dZRyKRs9ZHZYHzE<LWYS*evGR9bdD;Bgx<0^k;Z^SGW88`x0b_8q&!*hTU5?eTJtn9Uuj8HW>%<BDZ'
        'sXm)JTz5?x&8hAGZaZ=krTRn87usIj&In{`_X8$5!=Ly!=1>h$&H-Qa}fVCkorxN-'
        '%S%L!PC;@?DJ#`;<1}cc#Y_=hcaaX#c~+i{7NWj8bZ6E&otF-'
        '*9}Z^Xj&pqk_Cj}Auk;SWV&2w!{iV*N`FEhdAo*12B!2pxvc9FqyS>x9rmSI@-'
        'Eu%E9#NN3?@HzrnzcCkW3^7)8t)IZ5HEJiqCN>3m01uI~{Ax42uRMKbQ0Q*~Q9&hmK2_kS{-'
        '%GSw|W{eu$pC02we21V!#FLDWU0=iX*mb%hp%O9Epbi!$Wc`;ul|FrND5m$n8)zpVQ0azb)?O`{uaDkr5g)PM~hT'
        '^co%4s=~nU)XS-'
        'la}`)18y+Cr><D5Wrj0=kwY5lwt2;nkLUY+-F!QrM`Eduay=j7fC9pS->g!*&;c&Y@p`Ht;Aw`D9fxY-iZnQuJVd'
        't+#N$$^$rl`ZLLOb6L)%cT@_W4wWx2lU9oP5=a&^-'
        'r%f_8k>s>b{+@hOSHN2Qmzqq76!guT?u5ydwX6qtYNyfy`PG?afJD)5p=+I(+@-'
        'U;EGKC|X+j165^?hP&_0Q$i`hBw>~r}01Yv=mzZbvM#byFx;5MbE_M$<}D+9#!*MSb`&mrU$nB!QO_H5G{E2G+M0'
        '1WmGNrKx4AjrC`TcImY6UjjNWt(+%xwsH#7cbL9l&z4Ic%~t9#(|6}YeDmnK<zXG;BD4I`Xs^%iB>P?p)NbPP?Vy'
        'Y=s5^I(O_oSP<ENO1xT$0th)94j5Go20-'
        'vO2CE1Ct0Upn!SSC&<#cw{OEUHyvU%wa4oUo!4+ihG79knp%<BF;vnj7dtE-B$uVXKRpIQz})U-K^iOOx-'
        '!oXtzQ2qUMtt1@+ErWsBB<kA!9$02;qrB8(d$Idd6GAM=Q2sp6QDF>6fAZ+jW91pQIwdB6*05dh~-'
        'V1167!ZDsJQSxiB<a)v<#gL-5thgr^Eke0wkQUK#ccy)T7pnqVskV^um_gP{*t8Wwr-LN#)eBLXkVki_xm7+b}bh'
        '{mUjRiXQbJc0PP5%TDl_J+v33Ri0ItuHRU5=v#Kn4U-Um*OUmN9t~c2>-'
        'xcNEkwTKTN6Ku97KB7g>@rlatq+Y$;&3#g-'
        '5?p@l#wI1mowW^WwwTmZBtwxB)M_%3xtx(7>uH+13o=UHP$Mn9U~#DpjljIokUhv*`^<*Gpj{uriLUgV|s5|asjn'
        'OHe5v|iPXhldF88tR3#9iuTpr^n9txI(0jcp>JfD(fKYRI1|k;LS(k-'
        'A1PnEnHW1hs$@v_~=2U}X&hJQhN3<YV{yS2B--^Sg&YI^?He`4F7fdfE9b7@C1O%wN?z-'
        '>d5L^AD@a1w!nuyCg&)jx{%4wvZ$QsZ^$vP3Lxx9pQb5kO93}dh*2`aK*LzTEqk1D#X7pYrcwgMEp4bUw!h20iWc'
        '{&Eh6?IVGO^DP8WYKsY%BSIaQtY_ZWYTagD|g(gHhs80Ng%f_rMdO)z13Rjfm{umsA-'
        ')BhKZjKdDRuAP&=52iDJ+cuy5+i{IV#EuE1*AicZ@Wt&mA|fKqx50NR=nu>h!z0hFgg58TS{ip{<*s?OPDdz)mKr'
        '027jY_Ch{N`Y+)xjX^@1M8VrlI>O%`Ip9E1LZ}tpIB1i_Co_T=7KbpiV-'
        'V?I*~))l^#7d{eYS50{&3lypm@6In?OXP+6tTQ{VI!1MS4~{$gm-z5i$}54MJ&{kM`*mwB~$Uu?Q-'
        '&^@HdzPJ$?EVr$*yj|sowgq{bz1s+PAz*9XDGD!<MGkVisMs-vtK<+NXr(u1Y%__`vUod#1p)?V;>q)|>KPPK-'
        '}(xgo<mVf1-'
        'Fb#5)_9{f>+v1_Aw1%xMcoP?Bna`WV}DW7*Aozy*QU2FX`iz`gk>ttXp!A(kE(S|M~{&#DQ}VhK2e9muvawCH{FO'
        '|Ger!v?m#-*SeF|hOmIA1KR@k&h}q2OCWkfo_(nFHPe{*l~3d$Gpw>BsSh=^$K&x^LN`y^U0vgZyF9c-'
        'CEE5(<DC4P!Z~>-no5+Kg%bfPD`-t(Hj==8xE7XWQM1Yu1LFIlyb++D09_8HNU({kq=O1As4OL{3-'
        'uO=j_0DyMgo(Xk`y11n1Db$v|aM$f4oiFbzX`Y9{mB`s01{H_7_lppd~s@mN*JVN65KqiVbLSH+6xgB!HXz^plh+'
        'w+XJ!Wqx-'
        '?B>m~91dyuN1RZ5s2`iRRa<)A*Ql&%jx`jzxw=?Sdwy5$lk(Mk(NvUHkwA|GRZrYQ)5&29Lo>@c9LPpDnYmbq7r7'
        'r||y(dqe!_s6{o))HDqwPv5hZ5f(xJL@9;>kwud4eMd+XU5Ax^5adl%T0Zqng<fU68Kb{tPO>F29}V)})@Ts{Q;N'
        'X7A6RzI5=l!o)>-iWC32obI2#Q~-!&GRZCgWP-5H5G-zZFJ_;-'
        'c%@E3ARj5Zlpy73(>GYQCL!`u2e34=QSr}{^Oc1t)rM+9&}AvrklZ0)r(riSk#qwE1iJlvn!vu|4}`m&MGF*OP=b'
        'Iyku^POk2X&L@+6s@0TGn;r1frK)hj!SM70?LLG4HX1Vq!YVJu}tTVyHn+IS`_{1L6MN-'
        '{x@m~eFZJjG2C_8j{Bipr!UL`r1`z~XY(<zg;T1=K&0ikrcTus^`|wTX5%O`iHyw2{x*_Q}?#1c<370a9`%oh2`%'
        'wb{dhV<O8v^~;TvBmoT(B!*Ns6u-PUfAxo{Z06+!aKsBnO)UvFSNiO!gnIjY?P5Lk;68;xpvj-NFd`XMy$02zzJg'
        '7HnMhc8A%O?;*i@GkXxmxdc6WO*kz}@KCro<=V3}qk8Vm_}d9ebb(bw~p5)Z}IF4rWm?Dx#VQ0EPs;?SxgfW;k&<'
        '#zNe!DJlFwJ6HT3pv^rdaCGGZ?~=JTD=cJ)}5RY^r>#;DT3Ny9~aa|SyL^3vZA=%<7|6LXAMdmYS7P|W_jIb3-'
        'yid9JXW^pcR#ND|K~K!*V&HA)^}5w|XNMV=S(=NVH(17^kt}kd~?|bK56}TqLU2qUsvSPSh7QOn6WU71Wr`)kytw'
        '^6x_I6H(QNtLvmbbfA%;mQ$ApvrcL)f*|MR8OerUYFLxSji{3M*P>F;@?<OC!%iMB*a`0N1*7;*NaX-'
        '~ln{vBVSSwdKZs_=&mw!~0CEWvL+8(5sDW?@t@dcJ@lb@AdNgHRI892i?G|$OH^}Jtm0;qk&KF91^knuk`oIYf6|'
        'l5(nxJt4?!Zj%@X^2^_*U5H6n8l=oBcN5fiifKC%{8bDw!6#HZDqZEU^YAjp(v4U5njem#qb`C|a16)*9?b`&|s|'
        'o|9P?^bR$z-a&bD_|G?=TMLgC-'
        '!q%5dSBe+>pLxjGW}b+wqc@O1)X;6(&q0<qC~OT)Zt*C8PI4Er0A9MsCNMGQ(T@8ItL6@2Qk5Y0>~2gyLtvtlQ@U'
        '%$T(gA3MbbWpwFjZcJ7?9Jl<a*jmjkn=t4sC7UY2r#8LOp>J=T-iG9!uE8Pq|bd6D9H~iq6FOo4DE3BEqcsG$-'
        'l=9{LDBIJJVDP3qnwk2HQJ9C;7&?|fE60cXkGDqsh6gsvjHK~h^%;~(5Hi&-'
        '(4Uwrj~GW33ZsYESB}_KqLOT(DjgAX50-'
        '1LH7+V6^*`4kWI7r!>5Q*(0P+7+9Hio3au6Cv$k=xp^^lXOd&e1w=2&*ZtUB(lp(oX)sMgoJym>cvXVhu4X@CcgX'
        'T^s9V~761!#*(NeUpZb^huND{|J%1IpI)=*xcdc(Gd%9+-'
        'v6)y<BV}S&oC1TrF)8y;73Pa<(a8htLQz=P4gM*e)CBDL;bM+Z5%Gu|VBr?k!zv54_uVcciaGnqvM5^3>}_7=K#a'
        '{V=Ty7QqhpPZ1zXU3cX#o+bk-lFy&%0n39Ot@I0gN{ytnT`%jai~U5UoT)6ofqx9O@DCR+QF4Mkj}nYP#3%(Q7^G'
        'r^Ol=$3m(Ns7pSca8AA2P#-'
        'PBp)dd&<F*=}PB*tp}sHVsN*G1(O8khd5YS0K>E80GE_s(2<Pbv=@*!%j4LS2xB;vb&fV!~)tQ@ma1+v<Al}U%wN'
        'Q)eO{U35RCCpGj*X^Q{xPK4`vd^+11yw#FBZJ`MTR-'
        '2_W}9YNbaZb4+#B^FpY`3gD8anyMI&$kUph@sEOQ>PbX$i-'
        'T6@Tk%>`2;8EAJ~i;tj&`?i35Cr0H43`Af|mxYpR<GFg4?b;1x9@PJ>Nez+OaNX_D8JCS&5=9UkUf3iyu#u}UuFA'
        '<y%%vn7FMclj-fae4aCO3^kU++6b<of`y4ZLkLuS$@?BdHw9sqV^PD?Y>jB7AA_=*dwT~3cR&ap<9MLUcqh`U7N5'
        '=V`tlZjkXGDW0>i4BE_!QdM1FSO5fQV#CYJdeWCWA4>@Uay=Hl-'
        '<WE|DyB6Pc6!k*$s+#<0ZPlulQf7@}*m$kzq89F%hXV&3oM#!l>=flVq(}OA3Oo<jILLL~56Z!auRlWoH=?RR`%z'
        'NZ@BY(RAD)_))Uk$3M|rmNJbGNh8jJeK1so~M=*3@64rV!Bm&JZULWdFNS>m*FrrA1m#05c{dcbt*xvitb1gL%$>'
        'bJ0<fdIpO-'
        '9&qxbDt*1?Ob}hI0g;64vHIiUI{NcQhtqxrlmF%IUey56)xss<J|sG0!CV;ncYtd$0Z=YR1SNv|3Ui)q@c+Id$o!'
        'jY9J(T0(2o!&S{W_ed48Qdg_sbRqS`N9Ubv|w>>z)>D>};>e#^g9h_Y9hn`MI63zsp&|VOuEVDfs1JDUXKEWyZl)'
        'D0)X2<Rb_#|^x1)5(OThq`!&(~cC!`PC{8;Wfl`wTC`hz<K{J-'
        '|hIyvazQZ=&wTQCDMMPCmk$_)(t3zRe~a9q2=3$UM8FGf2`El_#9!@6>aM@=#x=6OWf3WnK37%T{aCzNhAHur%Du'
        '?U6eDL<h{GT6YXV>EY8Fg-xlh=5U{mt)X>XnxH7G6q9K0Qh8eo7WZc%`o1#|^BhpN45wXl=IGaeU45`L16sd`rf#'
        'LUrg2KO1Ol|pav{&i;-Mb`uN-A(ahoSd@2`teBxs0YZWj3^usw-OMIu{)&Z~hClFqJ7b@+FAguqKp1KHe)=&iiGA'
        'OXcMA+n0eJ9Jl5Ya8sOtGYs>O&DUI^$i<4#X%BFNZ!6v4Fw`-'
        'tH9O(50#L0WF6x=p#Z7^&h=QS@T1QfMr)w@7wmwD*Fs#Vzw+ksAPo9Eb71+`lJJ;3zRhq6-'
        '!2Wb)r#*x3^B0ILm)lvgVfgxq#j52vxVEJl)(lzS0dUd22wvz3A|0qNZC|RA(zFcYUrUnXh^M4_gsT3qoU1VCCZ4'
        'e?Zr&&MC7ihzCk=P<Qys_g(4ofI~Pms+`>l4ud#DiJ?Wq+3D%d3Rk<No-'
        'G5i)4syb}?gdt=Wz!<%ar2zfe6|&AqV_l=`fln2Ms9&=(fw)%o4@M~Sc*(gcP+Y}V3?M&SOdBoADi6@v~oQ31omT'
        'Z21xA~rw5)UhX=4}zm38<IPl$Bxgu<JJZx;vJYu1a0|oY%YK4pLq204%<>g9RxoJ<I7&EiK#D_+iE@TcO^ef%RjA'
        '6_#z*g>s*$``YOZJ$X(w4O>uUbA}jB2^TRx$KCS_g!6l*g^pB`xs>x#x(V9<^@asP9bd)aryoDD5RPaLxr&4OZK$'
        '?s{QSjqP1D8MDhf*<7%HA$ICT`eBIoB5!6%^fY>)C*dWD2hAq;dK)pw?@o!n>G^BY;>39xqX#X1zc*3hcX*&7Sny'
        'jO`#_0@9t(!IRp$4v`vO(;-?nvHJmp^P?>t_ibj0y8LnKd8Co#e163;O>$;C9*M11vec;ZnF^1ep;cqJ-'
        '+@YjGIR_|t@Tjii0WKDH7an%oZ(J~lFsUSVFW9WH%CFP)ij)J;%>GF03`t#&`%2tDEB7FjELh5-'
        'RKvL^10t)&x$}MRO5npXlVE@EdnmA*b5uFFT8Zr-Aw3db}tNy?btaE<~))ZwKd*-'
        '2k<gyz_Iktue)irc0wL$`g5{-'
        '~c2gqTXd@MbjWhEenMJYlMb<VO)_IZJqfu*A*tZU4fQy*DpH0@BS;qKo0Fe8@zWa^4~?F22`en5z*0hK9YEQm*WG'
        'GXH6<&21w(bAhlamcN9XSTV?t1hRzD+F@s69O-'
        'Xs4SO&EB7MK)LgHD8LO{^O>7JDHrP2`2YY4igN4D8$k?rZ(UqT(we33?M5ZXP4(mY7A@$yoa(-'
        '`nX1$D1;WWKige((rF$5}92hr<~5pKD9i5wmyMk)t`=Q&VZW%5u>c|+G%6Yj>rDyP0p|CkSc(8Pn?F(0P;9Py!iu'
        '<uzKA0nDm(fCHrFr|IN)DOTPsx%Tt2t^qZe#q41;W`alk3n`hDICXRdtI;9bkwUs%08e8$R}#dEam8sL5|x>UghP'
        'T)Jfg=8Ue5m(KTlboP)Rdqx{1{tc>TUTys~4vYF|mUk$cxM_ieeKdhQRgOCPhnTl(m)Cwbh`@uyapidkRqZC^d+&'
        'D|F)atpw|K!Ps-XH;6cKVuqkQUneNY}k<LQzP-)3UyQ!$2r3Ma0xKqb;y+q&8Z0Ux)ewDD-'
        '!gMbD|w#uFW+$zb)Um~r>S=)vetIX8b0e%hOR-yaQvPx;<b4;2NxUMN^ksVRlYhx=0_P23O29ChOeeR!1gnaQNfy'
        'NQ%1u&JpV6`{gh#a2J_md+i>g*jzcr;H*bom_?^_PJX$JS#@dR(Q?2I+MXf#wy5=?+Y5ZsgRmQrLB)jIQocMG!WT'
        'wZdZa9Ps(&Vn6gUcjo$uhDvAo$o9J_$5Qq+?FaXH6HY%Wl{BI9}hV+tUKVIqtv$v5Ugw4VebEfDiol)FtUdOYd4}'
        'ee}MRSiGf;DZG>dUvsAnH4rw3c0ongW;V5M|O21Fvfj4uXqKY-#imdK9(I;}<-'
        'ZlWgdy6m}4F7cjYrn8^w6>x%cW3C90DI~8!CLk@x-B0@xC;ERP}jX}KiNDZnVtI@;PoRb-uJ8;d9tib&ACrW9hgP'
        'h7^p6X$YbOTDqz$)9{$swKNxZcsLdpvx&{b3*0XjVsIrAJHXi4p8!hO6EW=ANdu98)9)CfNNE^PQoV3QaPscDp4`'
        'v=(qH_mL(dn?;Ub$P(@WYd_A+I5>dx@ew&?Z)jWCH^nY*?o1GZqxgHsc^g>@6m;?s^xFj<j8{n42xhS%A3(@4Yq='
        'PGw&+K99x?m87Y$|7TRi-RkVH4Aat*>XsN;8Xs3E5b2fx9#l7Wtmd_Fs^r$@1l_VoyT+@79>a-'
        '^@PkjPv=BLrc6I%pT^(_L$wb}58I5Wkm~d4R*MQxC)mBMq+2Ja>rM)qy~!%+=<%wp;fe9K;V0LSgUoL0Cf0*M*(6'
        ')8WbKqRhi0d&oy4suN1<LWSWTf2r!ApDdaVH)D_A!xrV8&_Sr%@duYI_sKTDsSnLCctZQLQ^5OF?QftxN&s}PE)O'
        'm6x?9&hHi*dDMJ(d>CEdynqkDSW&R$h??954g)5ysCaZJ1$&3fExKJ=s$`ic8#J#|AN1(n0Zp4xpf1nJY0)dR`D1'
        '<<e0`UiT0>vF$B9UlF~meJ`$?1GUk5XRTm-'
        ';dGI)Gl`WMm^LwxEUR^e+}FZdqgmGBbBXI`0TjeaYRKPyUNaBUytnSVm#5S-'
        'AzZQ8d#&y0y#1L&CI58t@jvNBU>^Pr~Mc=x=R5W&G-U(q?VNMycPw4>zghlrDY^$`r1=6c5*(RM-'
        'S9{AVkf9QMbft@4=CGM-fAF^xa&H?wF%1hEe?O#kGZJJDLVOIbhUreMlGX&;DxCM|!dEALE$Kye|yCzVPL3sutdg'
        '+ka(A8L}rb3jN$U>9Yatd)%NY_<Qy@98f&7R%V{mGoDM(5!1Pe@ooXgL!vphA{&R#x%PqurmZkA?OK&GuWW|*Z9f'
        '32lXv1SopadetVXCo7O1E26S0%Pv?tqre``pH<nQE%5;nPvHsrLi>W9r<L<}JN)G@Ki(m{CAJ*-'
        '%t01uHIghrlm0U#AG*erf3KATKVJ$V|1i;oNZ9o>N7FM9i=iH$<+>)X6d6Rc$etyZ~eG5U6!b5$Ccf{JRsqo-'
        ')4BH&zrun&>Bue$Olb63G#0X}tlZwfetth>xwzJn_RGLN?+@8lz%uxjU5K-'
        '0rU{!kBZ@<8~Ttt=(F>v|)L&@&qL?I|njriuH8uQZ+Nm(qeba5$<?@tLJnd@~fd;>cN#=CD3EGm;DIdVdEhli0IY'
        '?i31cPvt?R7AO9NEl66r#aI4YQc6@>l3)qKp{&=-'
        '`Baa>YKDi5nL4m`Z`rv+qK9hL7foqN;gsZ!Kd+GU`iB=ZO2(N{r<q>Vs(wkn%L~w*Bnh%s;G>!obtluL&wHPPe)7'
        'n`galV!^)#)_)JJS&&1FX_vmDEW@k&Qm2JoqoaFPe8fMi!{%atrGs69Z37Oz>08-'
        'jgqa&R1#W3?lU6dLSw+cK1@=k-'
        'Yiq~+|X3r6Qd7z74&rmGrca$ZWvsy}Ulk2V*LkSpd66eY3IpvUYACJ1bFBBYFEsAa7{<WIs&n7HoB$Jp6fc#LN98'
        '2BI9O6p%GG-IqtfwKh*u4Vv4-}akqn%bYjmXhk*=~W-ZC-yNFebtKmsnIo`>ZfTM1Rh>k<wv2Hda-'
        'Rez4fhVivlf+Arj{PG)CvdS&nvx%e-k(Vo<-(Y9PO;fTPshy-zs9y52p0<tK=6^_A=_;0OQp6pcSrB7fgZA8a3XW'
        'B+!$G$uvZKjigWHb%EVoPZpb+>SKXci(MTW9`W6`eHC@n)<FK>H!#-'
        '0grSoGWd~FOY^49gZRK53(XW7)HHljC)zacoma<lkw27rvg;=(EL@i31jQXWnB1}mfIjz*eA5a&_M=BbuAotz$Lq'
        'pud(8}&zgM30mx(dy?*h}iVGWFad%!612r%Ou;**n4A^nx*25%j)JT>4B@x=~ZxYsk>Ph-gBafb3C;cp9#b)lZR?'
        'u+rQs5-M-=E?xi<DAc1a#W{zWHqNOj+=h6&B4rjvuzwKH5iJ+PxHzf$*0Pi-'
        'x0XfT~|p9tT<||*0Vs#uu*vQ92%K1B;bJ~4FG187%@pVA}4b+FHMQD7aiR(<8^pe?+bW3_+~`^>l^Zz0@$nDDecy'
        'i8Y<OB#tQjT-eRlB)QanpjF~qMx9P43>x!;Keo_s10xrKTTDrxKl9P!WuUsQkfJf5bp)dx{3gxeb^^HU{*%lpYUK'
        'U@kk_2aK{e_D6BLa%0h}v1lZ*?6|(edqrq;fD&YT>`w1q2v&BieOS>}5IJYKhw}39ko^(TVfW0$6-'
        'UqLJ73)$Ja+9aJsUmw&?+X5--'
        '}y@o~?bd9c%QQFXDQOJ{oQ^$AwK@IVJ^56fJC`bu|G&uBcMGFJe^0zaN^MEVkBTVq!Q7pXiKLL$?4hUPLhr{UTx('
        'Pu~<vu0X12`V_ooxUk9%Y=58TWj>KI{%<F2h=3TuoK#v7^u6sraJ`-XIUWiIxe6{rt$(|Kh~fy|Irs-'
        '#^@a&EWXp8!R&H5-dy@REL6Nw*Onk+dTJ{88^<y4z<|r3)=k}pos-KJl>|No*Tcylz;OOe0&Ztb$e^{v%?S9g)}|'
        'n)i6!yQNKWvlPrh{f6Xo=Mrb%cnmfW>LErfLv*OsKJvL$8@j6X;o=N1Kt;Vs*t4E5)MTO_I6VxCnA2h@%dICv@RI'
        '>+$+Bwk}{cs~*^ib#WE>mNA^2@i6wJ}SDMCp2bbZu-'
        '&Q<vpN9xZY42IlD09sG#_|KUFM48OhRQs<=5mig80Kswz9v}v;9&2rm?po^N}r7?)GUE19t1<|Br1xZ3RcdqWa*;'
        '0mK)9}*db3gi7V7VNHSILktXKJ|gHbD!6e`@ZN>l_i0HmR<_a{$|ceBEFu33>)*9+6{D6P(Mlzt#AXBuoaeVd$n2'
        'ifRdE7}rvAsXkYn?CdcdmC_<zSgr+Nrm#F_&&hLL^QD=~EYlud#^3Srg(>o*KE)>pGuO2ZRc+7_q}7F@NZFDqtH)'
        '%(OU6tFW!+`UGT{K#>9Nhe1JmE^YgN$N*?95L=zvetX8ElM?-Jly9j+efoCiEq(W|UcM?Ss>#dv@n-'
        'lS<Dj8qb}+(hx#_Cez?=%({Sgs4GD+wyzBYumFAo}DfXg4gjzjCm#C61M~&0GX0)iu|go<qI@{!V*O}s1|pu>?_@'
        'SsW9}x;mB?Q9wNB>FxHDXCe7rJsaofCqWp1Bvp%Oah2tb)t+>@MZz@<@qx92xzQKiy1T6_pTCID<gBFS>th|RRzs'
        'ZY|yf!>14GhH1%;>-'
        'JL9p$$7sP?E_tx3arbeD#CkxcjOU{NSV#Oj_1IIKF0In^KQF8_gTyP6hJ+p>tC?lk`_aSs;=(`WDk!mjx4?WgqFn'
        'ti*I^XA)MJZ1%7RvEU^=2GD4`z?S(HB6GwF1fPmuBP3Ls4$Xb#y~&Lq^*TqQJJ1!^Qm;9A#67cz-'
        'R=&cAK`%3`Onn^@j_a7(L+=p0MMA?o!y9(7(m&I&x#UC)(U$#=PayZNMvsg9u3S(95a!(&>}cD!v}@hxS^M^TiNp'
        'l5OYUc?&kPVTUZPWTbyoJFeCdqvbA?F$;TbNH5W{7O>d1cl#{dy0+&{hyeHkJ*ZHdxl#XQ1W2cWA~$K8!ES@#4u{'
        'BNtCx?pym6x_(--w6!6gBU_SIAt!5{wW_Yzizo(`cGNT+jGq;VSDJefZ-'
        '~Wzr;evgivZHmzcMIp2Eu=Ybp}(*v!R1gd=%e>N)P?t()u-'
        '++e5&za{o3ZcNQh*w>9<D<9mz0Gn4b6;oIc?dO8>przDSRTKAvWM<bBu^-#hb9w--k}O2gfmPu|(Uc5UC(AR>2}j'
        '0_i4<hj!@ekD102DMCrewe^>0aa|Idd9gabtjcsxfkfMRN@BKU0Nn1?v({>!h&n*x-'
        'btv+=uB#%JG(YcpPU*w~OK2U)^jSXTv|NhXh>=mhDg<;o%8Az4AT?Cmab+JM=`Iz1q|pS*Guuh6fLSETrwJ54bwv'
        'crgxu3@4?&W}OY0Z9Btw{c-'
        'HdnPS0z*dm<r3;u&M7jrCJL|rlirbziie{_nr7_hO$`W(RgH3WxVzO0@mdlcCv^mIwRF29g!%Y>;jDaLZhtIeSm%'
        '_P-BGci89R1~(1+ih_>lRgu$J68UZAI7umZdXd93Va#g54}{z8m0HjL?wN=B?uH65`>Bvr@G_5I0{^sZ$MQH_VmV'
        'X9MDr{Ono0GD`R7Ic>XD7V8Vd2at!J*rZ<68G8hUpoUrJxa?$l$M0>Gzw37A6w{v4JMf8>MQD*@fO!$CUkZ}J2TM'
        '82jT{?7V6hbR=SM0>Bs^3q3{NZ&vgVl43npQW#^mZ@Si*XCP{tA8c11$F0yXX*NhF3V4Cb5b~Y^KJZg_|0Ae<1tr'
        '?YDpa>dn{L_iw)b;+r47eEt1$kU4m)EN=BNTcy6(>{ExQ8$!W)kWmsZWo1{u`+T8vuUyQo1s4boJ<~7@DPKRy!x|'
        'R`>r*{s=i(A`>|BlDIZluGp3}Wd!E$&F^hY!iu&@dX_~GQm7TD-'
        '>wE<~37%x1bGiLT)AHzYXhD!un=cDQ`%a4UgIX%2$U%w1$VaU9XQ)V5%JABw!4ou`l`^St1f%z>_X75xW-'
        'o4LOJc^eXu&@u0)QnElj!w{!%;{F-_FZHsEbkq^uIGlPJ`ore{SAiso@qboOk=itw<(&5I^a+d-'
        'o!0T{j7e+e8p8IX-'
        '&xFj<`XOnkHj!i)N_1OqlReYy)d0s5dY}@utT3&~4BD=)T3;V=%Go#<ZmceP?<kEf5R!X)~;}Uf8dW(oEXLVnDa('
        'QyLa0DHV7DD$DS$BECYuB>PX$S*a1Klk9Py&89b>NTsuTjf_xWHToa4A3uB'
    ),
}
# fmt: on


def _new_package(name: str) -> None:
    if name in _sys.modules:
        return
    package = _types.ModuleType(name)
    package.__file__ = f"<embedded-package:{name}>"
    package.__package__ = name
    package.__path__ = []
    _sys.modules[name] = package


def _load_embedded_runtime() -> None:
    _new_package(_RUNTIME_PREFIX)
    _new_package(f"{_RUNTIME_PREFIX}.reporting")
    for name, payload in _EMBEDDED_SOURCES.items():
        if name in _sys.modules:
            continue
        module = _types.ModuleType(name)
        module.__file__ = f"<embedded:{name}>"
        module.__package__ = name.rpartition(".")[0]
        _sys.modules[name] = module
        try:
            source = _zlib.decompress(_base64.b85decode(payload)).decode("utf-8")
            exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102
        except Exception:
            _sys.modules.pop(name, None)
            raise


_load_embedded_runtime()
_core = _sys.modules[f"{_RUNTIME_PREFIX}.reporting._core"]
_evidence = _sys.modules[f"{_RUNTIME_PREFIX}.reporting.evidence"]

UnderwriterReportError = _core.UnderwriterReportError
UnderwriterReportOptions = _core.UnderwriterReportOptions
UnderwriterReportResult = _core.UnderwriterReportResult
build_scored_model_report = _core.build_scored_model_report

CapabilityUnavailable = _evidence.CapabilityUnavailable
EvidenceFact = _evidence.EvidenceFact
EvidenceRequest = _evidence.EvidenceRequest
ExactLossEvidence = _evidence.ExactLossEvidence
FeatureImportanceEvidence = _evidence.FeatureImportanceEvidence
InteractionEvidence = _evidence.InteractionEvidence
MainEffectEvidence = _evidence.MainEffectEvidence
ModelEvidence = _evidence.ModelEvidence
SuppressionMetadata = _evidence.SuppressionMetadata

ProblemType = Literal["frequency", "severity", "burn_cost"]
ColumnOrValues = str | Sequence[float] | np.ndarray | pd.Series
ComparisonUnit = str | Sequence[Any] | np.ndarray | pd.Series
_ALLOWED_SECTIONS = {"report", "data", "columns", "predictions"}
_ALLOWED_KEYS = {
    "report": {
        "output_path",
        "title",
        "model_type",
        "tweedie_power",
        "top_k",
        "double_lift_bins",
        "curve_bins",
        "distribution_bins",
        "movement_bins",
        "comparison_bootstrap_replicates",
        "comparison_bootstrap_seed",
        "minimum_cell_size",
    },
    "data": {"path"},
    "columns": {"actual", "sample_weight", "features", "comparison_unit", "offset"},
}


def build_report(
    frame: pd.DataFrame,
    *,
    actual: ColumnOrValues,
    predictions: Mapping[str, ColumnOrValues],
    sample_weight: ColumnOrValues,
    features: Sequence[str],
    model_type: ProblemType,
    output_path: str | Path,
    offset: ColumnOrValues | None = None,
    comparison_unit: ComparisonUnit | None = None,
    evidence: Mapping[str, ModelEvidence] | None = None,
    title: str = "Pricing model review",
    tweedie_power: float | None = None,
    minimum_cell_size: int = 20,
) -> UnderwriterReportResult:
    """Build a self-contained aggregate report from already-scored predictions."""
    options = UnderwriterReportOptions(
        title=title,
        problem_type=model_type,
        tweedie_power=tweedie_power,
        minimum_cell_size=minimum_cell_size,
    )
    return build_scored_model_report(
        frame,
        actual=actual,
        predictions=predictions,
        sample_weight=sample_weight,
        features=features,
        output_path=output_path,
        evidence=evidence,
        offset=offset,
        comparison_unit=comparison_unit,
        options=options,
    )


@dataclass(frozen=True)
class PortableReportConfig:
    data_path: Path
    output_path: Path
    actual: str
    sample_weight: str
    features: tuple[str, ...]
    predictions: dict[str, str]
    options: UnderwriterReportOptions
    comparison_unit: str | None = None
    offset: str | None = None


def _required_string(table: Mapping[str, Any], key: str, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _config_path(
    raw_value: Any,
    *,
    label: str,
    relative_to: Path,
    suffixes: tuple[str, ...],
    suffix_message: str,
) -> Path:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{label} must be a non-empty path")
    path = Path(raw_value.strip()).expanduser()
    if not path.is_absolute():
        path = relative_to / path
    resolved = path.resolve()
    if resolved.suffix.lower() not in suffixes:
        raise ValueError(f"{label} {suffix_message}")
    return resolved


def _features(raw_value: Any) -> tuple[str, ...]:
    if (
        not isinstance(raw_value, list)
        or not raw_value
        or not all(isinstance(value, str) and value.strip() for value in raw_value)
    ):
        raise ValueError("[columns].features must be a non-empty string array")
    resolved = tuple(value.strip() for value in raw_value)
    if len(set(resolved)) != len(resolved):
        raise ValueError("[columns].features must not contain duplicates")
    return resolved


def _predictions(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict) or not raw_value:
        raise ValueError("[predictions] must be a non-empty table")
    resolved: dict[str, str] = {}
    for raw_name, raw_column in raw_value.items():
        name = str(raw_name).strip()
        if not name or not isinstance(raw_column, str) or not raw_column.strip():
            raise ValueError("[predictions] must map non-empty names to non-empty column names")
        if name in resolved:
            raise ValueError(f"[predictions] contains duplicate normalized model name: {name!r}")
        resolved[name] = raw_column.strip()
    return resolved


def _optional_number(raw_value: Any, label: str) -> float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        raise TypeError(f"{label} must be numeric, not boolean")
    if not isinstance(raw_value, int | float):
        raise TypeError(f"{label} must be numeric")
    return float(raw_value)


def load_config(path: str | Path) -> PortableReportConfig:
    """Load a prediction-only portable report TOML file."""
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)
    unknown_sections = set(payload) - _ALLOWED_SECTIONS
    if unknown_sections:
        raise ValueError("unknown TOML sections: " + ", ".join(sorted(unknown_sections)))
    for section, allowed_keys in _ALLOWED_KEYS.items():
        section_payload = payload.get(section)
        if not isinstance(section_payload, dict):
            raise TypeError(f"TOML section [{section}] must be a table")
        unknown_keys = set(section_payload) - allowed_keys
        if unknown_keys:
            raise ValueError(f"unknown [{section}] keys: " + ", ".join(sorted(unknown_keys)))
    report = payload["report"]
    data = payload["data"]
    columns = payload["columns"]
    title = report.get("title", "Pricing model review")
    if not isinstance(title, str):
        raise TypeError("[report].title must be a string")
    title = title.strip()
    if not title:
        raise ValueError("[report].title must be non-empty")
    model_type = report.get("model_type")
    if model_type not in {"frequency", "severity", "burn_cost"}:
        raise ValueError("[report].model_type must be frequency, severity, or burn_cost")
    features = _features(columns.get("features"))
    predictions = _predictions(payload.get("predictions"))
    comparison_unit = columns.get("comparison_unit")
    if comparison_unit is not None:
        if not isinstance(comparison_unit, str) or not comparison_unit.strip():
            raise ValueError("[columns].comparison_unit must be a non-empty string")
        comparison_unit = comparison_unit.strip()
        if comparison_unit in features:
            raise ValueError("comparison_unit must not also appear in features")
    offset = columns.get("offset")
    if offset is not None:
        if not isinstance(offset, str) or not offset.strip():
            raise ValueError("[columns].offset must be a non-empty string")
        offset = offset.strip()
    options = UnderwriterReportOptions(
        title=title,
        problem_type=model_type,
        tweedie_power=_optional_number(report.get("tweedie_power"), "[report].tweedie_power"),
        top_k=report.get("top_k", 12),
        double_lift_bins=report.get("double_lift_bins", 10),
        curve_bins=report.get("curve_bins", 100),
        distribution_bins=report.get("distribution_bins", 200),
        movement_bins=report.get("movement_bins", 10),
        comparison_bootstrap_replicates=report.get(
            "comparison_bootstrap_replicates",
            200,
        ),
        comparison_bootstrap_seed=report.get("comparison_bootstrap_seed", 1729),
        minimum_cell_size=report.get("minimum_cell_size", 20),
    )
    return PortableReportConfig(
        data_path=_config_path(
            data.get("path"),
            label="[data].path",
            relative_to=config_path.parent,
            suffixes=(".csv", ".feather", ".parquet"),
            suffix_message="must end in .csv, .feather, or .parquet",
        ),
        output_path=_config_path(
            report.get("output_path"),
            label="[report].output_path",
            relative_to=config_path.parent,
            suffixes=(".html", ".htm"),
            suffix_message="must end in .html or .htm",
        ),
        actual=_required_string(columns, "actual", "[columns].actual"),
        sample_weight=_required_string(
            columns,
            "sample_weight",
            "[columns].sample_weight",
        ),
        features=features,
        predictions=predictions,
        options=options,
        comparison_unit=comparison_unit,
        offset=offset,
    )


def _read_configured_frame(config: PortableReportConfig) -> pd.DataFrame:
    required_columns = list(
        dict.fromkeys(
            [
                config.actual,
                config.sample_weight,
                *([config.comparison_unit] if config.comparison_unit else []),
                *([config.offset] if config.offset else []),
                *config.features,
                *config.predictions.values(),
            ]
        )
    )
    if not config.data_path.is_file():
        raise FileNotFoundError(f"configured input file does not exist: {config.data_path}")
    suffix = config.data_path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(config.data_path, columns=required_columns)
    if suffix == ".feather":
        return pd.read_feather(config.data_path, columns=required_columns)
    return pd.read_csv(config.data_path, usecols=required_columns).loc[:, required_columns]


def build_report_from_config(config: PortableReportConfig) -> UnderwriterReportResult:
    """Read configured scored columns and build the portable report."""
    return build_scored_model_report(
        _read_configured_frame(config),
        actual=config.actual,
        predictions=config.predictions,
        sample_weight=config.sample_weight,
        features=config.features,
        output_path=config.output_path,
        offset=config.offset,
        comparison_unit=config.comparison_unit,
        options=config.options,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a self-contained model review from scored predictions."
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to report TOML")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    result = build_report_from_config(load_config(args.config))
    print(f"Report: {result.output_path}")
    print(result.metrics.to_string(index=False))


__all__ = [
    "SOURCE_SHA256",
    "CapabilityUnavailable",
    "EvidenceFact",
    "EvidenceRequest",
    "ExactLossEvidence",
    "FeatureImportanceEvidence",
    "InteractionEvidence",
    "MainEffectEvidence",
    "ModelEvidence",
    "PortableReportConfig",
    "SuppressionMetadata",
    "UnderwriterReportError",
    "UnderwriterReportOptions",
    "UnderwriterReportResult",
    "build_report",
    "build_report_from_config",
    "build_scored_model_report",
    "load_config",
]


if __name__ == "__main__":
    main()
