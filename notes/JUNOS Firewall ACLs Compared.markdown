So I bet you’re wondering what exactly the difference is between
Trigger’s current JUNOS firewall support and what we want to add to it
(namely, stateful SRX). Well, wonder no more, because what follows is a
breakdown of these differences. And boy, what a difference it is!

But before diving into the differences, we first need to get a full
picture of what a stateless firewall configuration looks like.

Intro to \*\*Stateless\*\* JUNOS Firewall ACLs (CURRENTLY SUPPORTED)
====================================================================

*(the following is sourced from*
[*http://robertjuric.com/2010/09/19/junos-firewall-filters/*](http://robertjuric.com/2010/09/19/junos-firewall-filters/)*)*

Stateless JUNOS firewall ACLs (AKA “firewall filters” in the official
terminology) can be one of three different types of filters:

1.  Port (layer 2) filters,

2.  VLAN filters, or

3.  Router (layer 3) filters.

> *“Port firewall filters are applied to layer 2 switch ports, only in
> the ingress direction. VLAN firewall filters can be applied to both
> ingress and egress directions on a VLAN. Router firewall filters can
> be applied to the ingress or egress directions on layer 3 interfaces
> and RVIs (routed vlan interfaces), they can also be applied to the
> ingress direction on a loopback interface.”*

First you “must configure the firewall filter and then apply it at the
correct level. You are only able to apply one firewall filter per
port/vlan/router interface, per direction [hence
“unidirectional/stateless”]. However the filter is able to support up to
2,048 terms.”

Example firewall filter syntax:

firewall {

family [inet/ethernet-switching] {

filter \<filtername\> {

term \<termname\> {

from {

\<match conditions\>

}

then {

\<action\>

}

}

}

}

}

Each filter definition can have multiple terms. Each term can have one
from {…} field, and one then {…} field. The “level” at which the filter
term applies is specified in the from {…} field (see
<https://web.archive.org/web/20100606192655/http://jnpr.net/techpubs/en_US/junos/topics/reference/requirements/firewall-filter-ex-series-match-conditions.html>
for a list of valid levels). An example from {…} field from the blog
post is below:

from {

protocol [tcp udp];

source-port 123;

}

Relevant Trigger code for stateless JUNOS Firewall Filters
----------------------------------------------------------

Parsing: See trigger/acl/parser.py, lines 2045-2174. Output: see
trigger/acl/parser.py, lines 796-851

from {…} matching order: trigger/acl/parser.py, lines 1378-1401; Output:
trigger/acl/parser.py, lines 1568-1596.

Further Reading
---------------

-   Stateless Firewall Filter Overview:
    <http://www.juniper.net/techpubs/software/junos-es/junos-es90/junos-es-swconfig-interfaces-and-routing/stateless-firewall-filter-overview.html>

-   Stateless Firewall Filter Actions and Action Modifiers:
    <http://www.juniper.net/techpubs/software/junos-es/junos-es90/junos-es-swconfig-interfaces-and-routing/stateless-firewall-filter-actions-and-action-modifiers.html>

### BONUS: Cool python code in Trigger

In trigger/acl/parser.py, lines 1855-1862:

> unary\_port\_operators = {
>
> 'eq': lambda x: [x],
>
> 'le': lambda x: [(0, x)],
>
> 'lt': lambda x: [(0, x-1)],
>
> 'ge': lambda x: [(x, 65535)],
>
> 'gt': lambda x: [(x+1, 65535)],
>
> 'neq': lambda x: [(0, x-1), (x+1, 65535)]
>
> }

Intro to \*\*Stateful\*\* JUNOS Firewalls (\>NOT\< SUPPORTED)
=============================================================

Stateful firewalls, and their corresponding ACLs, are somewhat more
complicated than their stateless counterparts. Instead of being a single
chunk, stateful (aka bidirectional) firewall ACLs have multiple
components. This is necessary because of the need to define “zones” from
and to which traffic is directed.

Example Stateful Firewall Configuration
---------------------------------------

Compare the previous example of a stateless firewall filter with this
example of a stateful SRX firewall:

90 security {

91 inactive: idp {

92 security-package {

93 url https://services.netscreen.com/cgi-bin/index.cgi;

94 }

95 }

96 policies {

97 from-zone untrust to-zone trust {

98 policy 3 {

99 match {

100 source-address 1.2.3.4;

101 destination-address AddrObject;

102 application APPNAME;

103 }

104 then {

105 permit;

106 log {

107 session-init;

108 session-close;

109 }

110 }

111 }

112 policy 4 {

113 match {

114 source-address 1.2.3.4;

115 destination-address any;

116 application APPNAME2;

117 }

118 then {

119 permit;

120 log {

121 session-init;

122 session-close;

123 }

124 }

125 }

126 policy 2 {

127 match {

128 source-address any;

129 destination-address any;

130 application any;

131 }

132 then {

133 deny;

134 }

135 }

136 }

137 from-zone trust to-zone untrust {

138 policy 5 {

139 match {

140 source-address SOURCE;

141 destination-address DEST;

142 application Appname3;

143 }

144 then {

145 permit;

146 log {

147 session-init;

148 session-close;

149 }

150 }

151 }

152 policy 1 {

153 match {

154 source-address any;

155 destination-address any;

156 application any;

157 }

158 then {

159 deny;

160 }

161 }

162 }

163 }

164 zones {

165 security-zone trust {

166 address-book {

167 address 2.3.4.5 2.3.4.5/32;

168 address 3.4.5.6 3.4.5.6/32;

169 address SOURCE 4.5.6.7/16;

170 address-set AddrObject {

171 address 2.3.4.5;

172 address 3.4.5.6;

173 }

174 }

175 host-inbound-traffic {

176 system-services {

177 all;

178 }

179 }

180 interfaces {

181 INTER;

182 }

183 }

184 security-zone untrust {

185 address-book {

186 address 1.2.3.4 1.2.3.4/32;

187 address DEST 4.5.6.7/16;

188 }

189 interfaces {

190 INTER;

191 }

192 }

193 }

194 }

### 

### Example syntax:

TO BE CREATED…IF WE CAN FIGURE IT OUT!! (mainly I didn’t attempt this
due to a misunderstanding of SRX firewall {…} and security {…} sections;
see below in “Open Questions, Remarks”.

Analysis, Comparison
--------------------

### “policy” vs. “term”

There seems to be a rough correspondence between the stateless “term”
sections and stateful “policy” sections, in that both have a matching
subsection followed by an action subsection. However, they are still
quite different, because the stateful “policy” sections lie within
from-zone/to-zone sections. In essence, the stateful “policy” sections
seem to be drilling down deeper into their parent from-zone/to-zone
sections, whereas the stateless “term” sections simply match some source
or destination directly.

### Zones, and NetScreen similarities

I think I now understand what Jathan meant when he stated that the SRX
configurations were similar to the NetScreen configurations. Both have
some kind of concept of “zones.” This is readily apparent when you look
at the NetScreen/SRX comparison PPT. However, it truly stands out once
you’ve seen how zones are absent from stateless JUNOS firewall
configurations.

Questions, Remarks
------------------

-   Q: I’ve seen some example SRX firewall configurations online that
    use the firewall {…} top-level section and the policer (as opposed
    to the configurations, which use the security {…} top-level). What’s
    the difference? Does setting the security {…} section have the
    effect of automatically generating associated firewall rules? I.e.,
    is security {…} an abstraction of more granular firewall rules? Or
    is it something else?

    -   A : The SRX “firewall” stanza referred to on the web page are
        used for assigning rate limiting and are unrelated to policies
        which define access control though the firewall, traversing from
        one zone to another. It is unfortunate JunOS used the directive
        “firewall” for the rate limiting function. I would have to ask
        my Juniper support engineer the reason behind this.

-   Q: I can see how Trigger is parsing the Junos firewall directives at
    the term level. However, what isn’t clear to me is how Trigger
    parses them at the filter and firewall levels. Where is the relevant
    code for this?

### 
