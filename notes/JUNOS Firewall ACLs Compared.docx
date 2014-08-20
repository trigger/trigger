<p>So I bet you’re wondering what exactly the difference is between Trigger’s current JUNOS firewall support and what we want to add to it (namely, stateful SRX). Well, wonder no more, because what follows is a breakdown of these differences. And boy, what a difference it is!</p>
<p>But before diving into the differences, we first need to get a full picture of what a stateless firewall configuration looks like.</p>
<h1 id="intro-to-stateless-junos-firewall-acls-currently-supported">Intro to **Stateless** JUNOS Firewall ACLs (CURRENTLY SUPPORTED)</h1>
<p><em>(the following is sourced from</em> <a href="http://robertjuric.com/2010/09/19/junos-firewall-filters/"><em>http://robertjuric.com/2010/09/19/junos-firewall-filters/</em></a><em>)</em></p>
<p>Stateless JUNOS firewall ACLs (AKA “firewall filters” in the official terminology) can be one of three different types of filters:</p>
<ol style="list-style-type: decimal">
<li><p>Port (layer 2) filters,</p></li>
<li><p>VLAN filters, or</p></li>
<li><p>Router (layer 3) filters.</p></li>
</ol>
<blockquote>
<p><em>“Port firewall filters are applied to layer 2 switch ports, only in the ingress direction. VLAN firewall filters can be applied to both ingress and egress directions on a VLAN. Router firewall filters can be applied to the ingress or egress directions on layer 3 interfaces and RVIs (routed vlan interfaces), they can also be applied to the ingress direction on a loopback interface.”</em></p>
</blockquote>
<p>First you “must configure the firewall filter and then apply it at the correct level. You are only able to apply one firewall filter per port/vlan/router interface, per direction [hence “unidirectional/stateless”]. However the filter is able to support up to 2,048 terms.”</p>
<p>Example firewall filter syntax:</p>
<p>firewall {</p>
<p>family [inet/ethernet-switching] {</p>
<p>filter &lt;filtername&gt; {</p>
<p>term &lt;termname&gt; {</p>
<p>from {</p>
<p>&lt;match conditions&gt;</p>
<p>}</p>
<p>then {</p>
<p>&lt;action&gt;</p>
<p>}</p>
<p>}</p>
<p>}</p>
<p>}</p>
<p>}</p>
<p>Each filter definition can have multiple terms. Each term can have one from {…} field, and one then {…} field. The “level” at which the filter term applies is specified in the from {…} field (see <a href="https://web.archive.org/web/20100606192655/http://jnpr.net/techpubs/en_US/junos/topics/reference/requirements/firewall-filter-ex-series-match-conditions.html" class="uri">https://web.archive.org/web/20100606192655/http://jnpr.net/techpubs/en_US/junos/topics/reference/requirements/firewall-filter-ex-series-match-conditions.html</a> for a list of valid levels). An example from {…} field from the blog post is below:</p>
<p>from {</p>
<p>protocol [tcp udp];</p>
<p>source-port 123;</p>
<p>}</p>
<h2 id="relevant-trigger-code-for-stateless-junos-firewall-filters">Relevant Trigger code for stateless JUNOS Firewall Filters</h2>
<p>Parsing: See trigger/acl/parser.py, lines 2045-2174. Output: see trigger/acl/parser.py, lines 796-851</p>
<p>from {…} matching order: trigger/acl/parser.py, lines 1378-1401; Output: trigger/acl/parser.py, lines 1568-1596.</p>
<h2 id="further-reading">Further Reading</h2>
<ul>
<li><p>Stateless Firewall Filter Overview: <a href="http://www.juniper.net/techpubs/software/junos-es/junos-es90/junos-es-swconfig-interfaces-and-routing/stateless-firewall-filter-overview.html" class="uri">http://www.juniper.net/techpubs/software/junos-es/junos-es90/junos-es-swconfig-interfaces-and-routing/stateless-firewall-filter-overview.html</a></p></li>
<li><p>Stateless Firewall Filter Actions and Action Modifiers: <a href="http://www.juniper.net/techpubs/software/junos-es/junos-es90/junos-es-swconfig-interfaces-and-routing/stateless-firewall-filter-actions-and-action-modifiers.html" class="uri">http://www.juniper.net/techpubs/software/junos-es/junos-es90/junos-es-swconfig-interfaces-and-routing/stateless-firewall-filter-actions-and-action-modifiers.html</a></p></li>
</ul>
<h3 id="bonus-cool-python-code-in-trigger">BONUS: Cool python code in Trigger</h3>
<p>In trigger/acl/parser.py, lines 1855-1862:</p>
<blockquote>
<p>unary_port_operators = {</p>
<p>'eq': lambda x: [x],</p>
<p>'le': lambda x: [(0, x)],</p>
<p>'lt': lambda x: [(0, x-1)],</p>
<p>'ge': lambda x: [(x, 65535)],</p>
<p>'gt': lambda x: [(x+1, 65535)],</p>
<p>'neq': lambda x: [(0, x-1), (x+1, 65535)]</p>
<p>}</p>
</blockquote>
<h1 id="intro-to-stateful-junos-firewalls-not-supported">Intro to **Stateful** JUNOS Firewalls (&gt;NOT&lt; SUPPORTED)</h1>
<p>Stateful firewalls, and their corresponding ACLs, are somewhat more complicated than their stateless counterparts. Instead of being a single chunk, stateful (aka bidirectional) firewall ACLs have multiple components. This is necessary because of the need to define “zones” from and to which traffic is directed.</p>
<h2 id="example-stateful-firewall-configuration">Example Stateful Firewall Configuration</h2>
<p>Compare the previous example of a stateless firewall filter with this example of a stateful SRX firewall:</p>
<p>90 security {</p>
<p>91 inactive: idp {</p>
<p>92 security-package {</p>
<p>93 url https://services.netscreen.com/cgi-bin/index.cgi;</p>
<p>94 }</p>
<p>95 }</p>
<p>96 policies {</p>
<p>97 from-zone untrust to-zone trust {</p>
<p>98 policy 3 {</p>
<p>99 match {</p>
<p>100 source-address 1.2.3.4;</p>
<p>101 destination-address AddrObject;</p>
<p>102 application APPNAME;</p>
<p>103 }</p>
<p>104 then {</p>
<p>105 permit;</p>
<p>106 log {</p>
<p>107 session-init;</p>
<p>108 session-close;</p>
<p>109 }</p>
<p>110 }</p>
<p>111 }</p>
<p>112 policy 4 {</p>
<p>113 match {</p>
<p>114 source-address 1.2.3.4;</p>
<p>115 destination-address any;</p>
<p>116 application APPNAME2;</p>
<p>117 }</p>
<p>118 then {</p>
<p>119 permit;</p>
<p>120 log {</p>
<p>121 session-init;</p>
<p>122 session-close;</p>
<p>123 }</p>
<p>124 }</p>
<p>125 }</p>
<p>126 policy 2 {</p>
<p>127 match {</p>
<p>128 source-address any;</p>
<p>129 destination-address any;</p>
<p>130 application any;</p>
<p>131 }</p>
<p>132 then {</p>
<p>133 deny;</p>
<p>134 }</p>
<p>135 }</p>
<p>136 }</p>
<p>137 from-zone trust to-zone untrust {</p>
<p>138 policy 5 {</p>
<p>139 match {</p>
<p>140 source-address SOURCE;</p>
<p>141 destination-address DEST;</p>
<p>142 application Appname3;</p>
<p>143 }</p>
<p>144 then {</p>
<p>145 permit;</p>
<p>146 log {</p>
<p>147 session-init;</p>
<p>148 session-close;</p>
<p>149 }</p>
<p>150 }</p>
<p>151 }</p>
<p>152 policy 1 {</p>
<p>153 match {</p>
<p>154 source-address any;</p>
<p>155 destination-address any;</p>
<p>156 application any;</p>
<p>157 }</p>
<p>158 then {</p>
<p>159 deny;</p>
<p>160 }</p>
<p>161 }</p>
<p>162 }</p>
<p>163 }</p>
<p>164 zones {</p>
<p>165 security-zone trust {</p>
<p>166 address-book {</p>
<p>167 address 2.3.4.5 2.3.4.5/32;</p>
<p>168 address 3.4.5.6 3.4.5.6/32;</p>
<p>169 address SOURCE 4.5.6.7/16;</p>
<p>170 address-set AddrObject {</p>
<p>171 address 2.3.4.5;</p>
<p>172 address 3.4.5.6;</p>
<p>173 }</p>
<p>174 }</p>
<p>175 host-inbound-traffic {</p>
<p>176 system-services {</p>
<p>177 all;</p>
<p>178 }</p>
<p>179 }</p>
<p>180 interfaces {</p>
<p>181 INTER;</p>
<p>182 }</p>
<p>183 }</p>
<p>184 security-zone untrust {</p>
<p>185 address-book {</p>
<p>186 address 1.2.3.4 1.2.3.4/32;</p>
<p>187 address DEST 4.5.6.7/16;</p>
<p>188 }</p>
<p>189 interfaces {</p>
<p>190 INTER;</p>
<p>191 }</p>
<p>192 }</p>
<p>193 }</p>
<p>194 }</p>
<h3 id="section"></h3>
<h3 id="example-syntax">Example syntax:</h3>
<p>TO BE CREATED…IF WE CAN FIGURE IT OUT!! (mainly I didn’t attempt this due to a misunderstanding of SRX firewall {…} and security {…} sections; see below in “Open Questions, Remarks”.</p>
<h2 id="analysis-comparison">Analysis, Comparison</h2>
<h3 id="policy-vs.-term">“policy” vs. “term”</h3>
<p>There seems to be a rough correspondence between the stateless “term” sections and stateful “policy” sections, in that both have a matching subsection followed by an action subsection. However, they are still quite different, because the stateful “policy” sections lie within from-zone/to-zone sections. In essence, the stateful “policy” sections seem to be drilling down deeper into their parent from-zone/to-zone sections, whereas the stateless “term” sections simply match some source or destination directly.</p>
<h3 id="zones-and-netscreen-similarities">Zones, and NetScreen similarities</h3>
<p>I think I now understand what Jathan meant when he stated that the SRX configurations were similar to the NetScreen configurations. Both have some kind of concept of “zones.” This is readily apparent when you look at the NetScreen/SRX comparison PPT. However, it truly stands out once you’ve seen how zones are absent from stateless JUNOS firewall configurations.</p>
<h2 id="questions-remarks">Questions, Remarks</h2>
<ul>
<li><p>Q: I’ve seen some example SRX firewall configurations online that use the firewall {…} top-level section and the policer (as opposed to the configurations, which use the security {…} top-level). What’s the difference? Does setting the security {…} section have the effect of automatically generating associated firewall rules? I.e., is security {…} an abstraction of more granular firewall rules? Or is it something else?</p>
<ul>
<li><p>A : The SRX “firewall” stanza referred to on the web page are used for assigning rate limiting and are unrelated to policies which define access control though the firewall, traversing from one zone to another. It is unfortunate JunOS used the directive “firewall” for the rate limiting function. I would have to ask my Juniper support engineer the reason behind this.</p></li>
</ul></li>
<li><p>Q: I can see how Trigger is parsing the Junos firewall directives at the term level. However, what isn’t clear to me is how Trigger parses them at the filter and firewall levels. Where is the relevant code for this?</p></li>
</ul>
<h3 id="section-1"></h3>
