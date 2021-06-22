## Regional cykelmodell 2.0

Utifrån utfallet av Kågesson-modellen 1.0 och de antaganden som skärskådades redovisas här en ansats till en regional cykelmodell 2.0. Den nya modellen beaktar exempelvis både cykel och elcykel för olika typer av ärenden, alltså inte bara pendling. Den nya modellen beaktar också olika grupper av människor utifrån exempelvis etnicitet, socioekonomi och ohälsa. Det är inte möjligt med tillgängliga data att beakta olika gruppers faktiska resmönster, däremot är det möjligt att beakta olika grupper när det gäller prioritering av infrastruktur. Såsom påpekats påverkas generellt socioekonomiskt svaga grupper mer av dålig infrastruktur. Från ett jämlikhetsperspektiv kan det då vara motiverat att satsa extra på svagare områden.

En utmaning är att göra välavvägda antaganden om hur länge och hur långt människor är villiga att cykla i relation till olika ärenden. Den här typen av information går inte att hämta från den svenska resvaneundersökningen. Istället har den nederländska resvaneundersökningen använts, se Figur   4 -23 och Figur   4 -24. Fördelen är dels att den nederländska resvaneundersökningen redovisar resmönster med både cykel och elcykel för olika typer av ärenden, dels att den nederländska cykelinfrastrukturen kan ses som en målbild.

.
.
.

### Modellen

Modellen är resultatet av ett examensarbete utfört av Laurent Cazor vid KTH. Huvudmålet för modellen är att rangordna nödvändiga förbättringar på basen av det relativa behovet för varje länk i vägnätet....


### Upskatta potentiellt behov av cykelvägar

Modellen är består av ett antal undermodeller för att beräkna behovet. Uppdelningen är både baserad på typen av ärende (pendlign till arbete, skolresor, turism, inköp och rekreation) och typ av cykel (vanlig cykel och elcykel). Orsaken till uppdelning baserat på cykeltyp beror på skillnaden i distans en person på vardera cykeltyp normalt färdas. De olika ärendena är baserade på den nationella resvaneundersökningen.

[fig]

Den modell som används för att uppskatta det potentiella behovet kallas fyrstegsmodellen. Denna modell är vedertagen i transportplaneringssammanhang och består av 4 nedan beskrivna steg där indata i det första steget är demografiska värden samt start- och målpositioner. Varje steg i modellen använder sig av resultetat från det föregående.

1. Resegenerering: Detta steg identifierar start- och målpositioner. Startpositioner är personers hem medan mål kan vara arbetsplatser, skolor, butiker, fritidsområden etc. Syftet med resegenerering är också att uppskatta antalet resor som varje ärende kan ge upphov till. Vikten av varje startposition är proportionerlig mot befolkningen och varje mål har samma vikt normaliserat till 1. Detta steg tillåter användandet av socioekonomiska variabler för att påverka vikten av startpositionen.

2. Resedistribution: I detta steg ämnar beräkna relationerna mellan start- och målpunkter samt sannolikheten att denna resa tas som en funktion av avståndet mellan en start- och målpunkt i relation till avstånden av övriga relationer i samma grupp. Modellen som används är en s.k. gravitationmodell. Utöver resultatet från föregående steg kräver även detta steg ett vägnätverk för att beräkna avståndet mellan start- och mål par.

3. Färdmedelsuppdelning: När start- och målrelationerna är kända (OD-par) kan sannolikheten för att en resa mellan ett par ska tas med cykel och elcykel beräknas. Detta modelleras på basen av faktiska resmönster sm en funktion av avståndet. Metoden som användas kallas "Binary logit model".

4. Summering: Antalet resor kan kan i det här steget beräknas genom att summera sannolikheten för varje OD-par per nätverkssegment. Summan representera det uppskattade dagliga flödet för varje del av vägnätverket.

Figure 2 visar ett flödesschema över varje steg beskrivet ovan.


[fig]


### Steg 1: Resegenerering

Målet med första steget är att identifiera resor och deras frekvens. Modellen har delats upp i flera undermodeller baserat på ärende:

- Arbetspendling
- Skolresor
- Inköp
- Övriga serviceärenden
- Rekreation
- Turism

Antalet resor per dag per person är baserat på den nationella resvaneundersökningen utförd 2019. Detta försäkrar att den beräknade mängden cykling överensstämmer med det potentiella dagliga flödet. För varje ärende $p$ definerar vi $T_p$ som antalet resor per individ per dag eller den s.k. resegenereringsfaktorn. Modellen gör antagandet att varje resa generera två enhetr _flöde_ (då varje mål kräver en tur- och en returresa). Undantaget är turismresor då de är mindre sannolika att generera returresor.

Den nationella RVUn skiljer inte på inköp och övriga ärenden samt rekreation och turism. Vi antar därför att fördelningen är 50/50 för inköp/övrigt och 75/25 för rekreation/turism. Tabellen nedan anger värdet för parametern $T_p$ för varje typ.

[table]

Det andra syftet med detta steg är att skapa start- och målpunkter. Vi definerar resegeneratorer och attraktorer för varje ärendetyp med antagandet att varje tur- returresa startar och återgår till en individs hem. Information om var individer bor aggregeras bl.a. på DeSO nivå. Sverige delas in i 5984 demografiska statistikområden vilka representerar mellan 700 och 2700 individer. Indelningen tar hänsyn till geografiska företeelser och begränsas i möjligaste mån av t.ex. vägar, vattendrag, järnväg etc. De är utformade att vara stabila över längre tidsrymder.

Målpunkter för arbetsplatser och skolor kan hämtas från SCB och då på nivån ruta. En ruta är ett område på 1000 m x 1000 m utanför tätort och 250 m x 250 m i tätort. Arbetsplatsmålpunkter kan delas in i 15 olika kategorier för att göra modellen mer detaljerad.

Övriga målpunkter kan hämtas från t.ex. OpenStreetMap, som är ett öppet fritt tillgängligt dataset, som innehåller en mängd klassade intressepunkter. Dessa OSM klasser kan kategoriseras för använding som målpunkter i modellen.


### Steg 2: Resedistribution

När de potentiella start- och målpumkterna är identifierad är nästa steg att modellera relationerna mellan dem i form av antalet resor mellan varje start- och målpunkt även kallat OD-par. Vi använder oss av en gravitationsmodell som säger att antalet resor mellan ett OD-par är proportionellt mot storleken på startpunkten, målpunkten och en generaliserad kostnadsfunktion mellan dem (vi använder oss av avståndet men även andra parametrar som höjdskilnad, säkerhet etc kan användas).

Matematiskt kan modellen beskrivas som följande: om $i$ är en startpunkt med storleken $O_i$ och $j$ är en målpunkt med storleken $D_j$ där avståndet  är $d_{ij}$ så är antalet resor mellan $i$ och $j$

$$
T_{ij} = A_i O_i D_j f(d_{ij})
$$

Där $A_i$ är en utjämningsfaktor som säkerstället att antalet resor som lämnar $i$ är lika med $O_i$. Vi får därmed

$$
A_i = \frac{
    1
}{
    \sum_j{D_jf(d_{ij})}
}
$$

Funktionen _f_ kallas avståndsavtagande vilken är en funktion vars värde avtar med avståndet. Vi väljer en exponentiellt avtagande funktion vars parameter är medelvärdet av den angivna reselängden för varje ärendetyp i den nationella RVUn.

$$
f: x \rightarrow e^{-\beta x}
$$

Värdet för $\beta$ anges i tabell 2

[tabell]


### Steg 3: Färdmedelsuppdelning

En färdmedelsvalsmodell, eller mer generellt en diskret valmodell, beräknar sannolikheten för att ett visst färdmedel ska användas som en funktion av olika parametrar; i det här fallet reslängd. [This given modal split will make competing for the bicycle with any other mode]. Färdmedlesfördelningen är baserad på individers faktiska beteende och beägenhet att välja ett visst färdmedel framom andra. Vi använder därför data från resvaneundersökningar för att beräkna parametrarna till sannolikhetsfunktionen. Vi har använt data från den nederländska resvaneundersökningen (OViN 2017) då RVU Sverige 2019 inte kunnat tillhandahålla tillräckligt detaljerad öppen data. Sannolikheten att en individ väljer cykeln som färdmedel för ett OD-par som funktion av avståndet ges av:


$$
P^{(i,j)}(bike)(d_{ij}) = \frac{
    1
}{
    1 + e^{-(\beta_0 + \beta_1 d_{ij} + \beta_2 d_{ij}^2 + \beta_3 \sqrt{d_{ij}})}
}
$$

[tabell]

Ett antagande som görs är att alla har tillgång till en cykel och en elcykel. Detta antagande kan modereras med en koefficient som reflekterar tillgången till cykel och, framför allt, elcykel (som troligtvis ändras snabbt). Koefficienten appliceras på de beräknade flödena för att erhålla en mer representativ fördelning.


### Steg 4:

Det sista steget går ut på att beräkna de resulterande flödena genom att summera antalet resor viktat med sannolilikheten att resan sker samt sannolikheten att resan sker med cykel eller elcykel.

Resorna knyts till det underliggande vägnätet (NVDB) genom att utnyttja Dijkstras algortim för att hitta den kortaste vägen mellan start och mål. Det underligganda antagandet är att varje individ väljer den kortaste vägen mellan varje punkt. Antagandet anses hålla givet att vi beräknar den potentiella efterfårgan med hypotesen är lika tillgängligt överallt. Vi återanvänder tdigare notationer och definerar $\alpha_m$ som proprotionen av färdmedel $m$ samt $T_p$ som antalet resor genererade per person och dag för ärende $p$. Flödet för länk $k$ i vägnätet kan då beräknas med följande formel:

$$
\text{flow}_k = \sum_{
    \substack{p \in ärende}\\
    \substack{m \in \{cykel, elcykel\}}\\
    (i,j) \in k
}{
    T_p \alpha_m T_{ij} P^{(i,j)(m)(d_{ij})}
}
$$

Formeln kan beskrivas som att flödet över länk $k$ är summan av:
- alla OD-par som använder $k$
- alla reseärenden

I den egentliga modellen är andelen resor med cykel respektive elcykel proprotionerligt mot deras marknadandelar vilket i Sverige är runt 80% för cykel och 20% för elcykel. Dvs

$$
\alpha_{cykel} = 0.8, \alpha_{elcykel} = 0.2
$$

Dessa värden antas ändra snabbt till elcykelns favör då undersökningar visar att runt 40% av alla svenskar övervägar att anskaffa en elcykel i framtiden.


## Inkludera socio-ekonomiska faktorer

Möjligheten att använda socio-ekonomiska faktorer för att förvränga storleken på startpunkten finns inkluderat i modellen. Förvrängningen har en direkt påverkan på det beräknade flödesvärdet för en länk [fig n] och kan således användas för att identifiera vägnätslänkar som kan påverka något rättvisemål. Tre indikatorer har använts för modifiera storleken på startpunkten på DeSO-nivå. Datan som krävs för att beräkna dessa indikatorer kan hämtas från SCB.

De beräknade indexen kommer alltid att medelvärdesnormaliseras med aveseende på det studerade området. Således kommer det totala antalet resor att hållas konstant vilket möjliggör enklare jämförelser.

Om $N$ är numret för DeSO-området och $X = (X_1, \dots, X_N)$ den realiserade variabeln $X$ i varje DeSO-område så kan medelvärdet skrivas som:

$$
\bar{X} = \frac{1}{N} \sum_{i = 1}^{N}{X_i}
$$


### Socio-ekonomisk status

Den socio-ekonomiska statusen är aggregationen av tre underindikatorer:

- utbildning: andelen gymnasieexamen
- anställning: sysselsättningsgraden
- ekonomiskt bistånd: graden av biståndberoende

Enligt tabellen nedan är varje DeSO-område rangordnat enligt dessa indikatorer. Området ges 1 poäng om det återfinns bland de 20% bästa, 3 poäng för 20% sämsta och annars 2 poäng.

[tabell]

Om $S$ är poängen enligt tabellen så kan indexet $s$ beskrivas som:

$$
s = \frac{S}{\bar{S}}


### Hälsostatus

Indikatorn knuten till hälsa beräknas som medeltalet av dagar sjukfrånvaro per invånare i DeSO-området:

$$
h = \frac{H}{\bar{H}}
$$



### Mångfaldsindex

Mångfaldsindex tar i beaktande individer med utländsk bakgrund för vilka tillgången till god cykelinfrastruktur utbildning är viktiga integrationsverktyg. Indexet består av proportionen $P$ utrikes födda och antalet $N$ nationaliteter i DeSO-området Mångfaldsindexet $d$ är åter igen normaliserat.

$$
d = \frac{
    P \times N
}{
    \bar{P} \times \bar{N}
}
$$

### Indexaggreggering


De tre indexen kombineras som ett aggregerat medelvärde $a$

$$
a = \frac{1}{3} (s+h+d)
$$

De olika indexen används som faktorer av startpunktsstorleken så att varje DeSO-omårde har ett individuellt korrigerade värden för populationen baserat på dimensionerna. Den förvrängda startpunktenstorleken för startpunkt $i$ av population $O_i$ gällande index $x_i \in \{a_i, s_i, h_i, d_i\}$ ges av produkten av denna faktor och populationen

$$
O_i^x = x_i \times O_i
$$

där

$s_i$ är det socioekonomiska indexet för startpunkt $i$\
$h_i$ är hälsoindexet för startpunkt $i$\
$d_i$ är mångfaldsindexet för startpunkt $i$\
$a_i$ är det aggregerade indext för startpunkt $i$\


## Utvärdera utbudet

### VGU-rekommendationer


